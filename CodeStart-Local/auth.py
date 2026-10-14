
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

auth = Blueprint("auth", __name__)
SCHEMA = """
        CREATE TABLE IF NOT EXISTS accounts(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0,
          session_version INTEGER NOT NULL DEFAULT 0, trail TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS challenges(
          id TEXT PRIMARY KEY, user_id INTEGER REFERENCES accounts(id),
          purpose TEXT NOT NULL, digest TEXT NOT NULL, expires REAL NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS throttle(
          bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL
        );
        """

GENERIC = "Se o e-mail puder receber esta solicitação, enviaremos um código. Confira também o spam."
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(24))


def db():
    conn = sqlite3.connect(current_app.config["AUTH_DATABASE"], timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_auth(app):
    folder = Path(os.environ.get("APP_DATA_DIR", str(Path(app.root_path) / "instance")))
    folder.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("SECRET_KEY", "").strip()
    if not key:
        keyfile = folder / "session.key"
        try:
            with keyfile.open("x") as stream:
                stream.write(secrets.token_hex(32))
            keyfile.chmod(0o600)
        except FileExistsError:
            pass
        key = keyfile.read_text().strip()
    app.secret_key = key
    app.config.update(
        AUTH_DATABASE=str(folder / "accounts.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1" if os.environ.get("CODESPACES") or os.environ.get("RENDER") else "0") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )
    with app.app_context(), db() as conn:
        conn.executescript(SCHEMA)
    app.register_blueprint(auth)

    @app.before_request
    def account_guard():
        g.user = None
        uid = session.get("uid")
        if uid:
            with db() as conn:
                row = conn.execute("SELECT * FROM accounts WHERE id=?", (uid,)).fetchone()
            if row and row["verified"] and session.get("version") == row["session_version"]:
                g.user = dict(row)
            else:
                session.clear()
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            given = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not given or not hmac.compare_digest(given, session.get("csrf", "")):
                if request.path.startswith("/api/"):
                    return jsonify(success=False, error="Sua sessão expirou. Recarregue a página."), 400
                return render_template("auth.html", mode="login", error="Sua sessão expirou. Recarregue a página."), 400
        public = request.endpoint and (request.endpoint.startswith("auth.") or request.endpoint == "static" or request.endpoint == "health")
        if not public and not g.user:
            if request.path.startswith("/api/"):
                return jsonify(success=False, error="Entre na sua conta para continuar."), 401
            return redirect(url_for("auth.login"))

    @app.context_processor
    def auth_context():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        user = None
        if g.get("user"):
            user = {"id": g.user["id"], "name": g.user["name"], "trail": json.loads(g.user["trail"])}
        return {"csrf_token": session["csrf"], "account_data": user, "mail_ready": mail_ready()}

    @app.after_request
    def auth_headers(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response


def text_field(name):
    value = request.form.get(name, "")
    return value.strip() if isinstance(value, str) else ""


def email_field():
    value = text_field("email").lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Digite um e-mail válido.")
    return value


def password_field():
    password = request.form.get("password", "")
    if len(password) < 10 or len(password) > 128:
        raise ValueError("Use uma senha entre 10 e 128 caracteres.")
    if password != request.form.get("confirm_password"):
        raise ValueError("As senhas precisam ser iguais.")
    return password


def allow(bucket, maximum, seconds):
    key = hmac.new(current_app.secret_key.encode(), bucket.encode(), hashlib.sha256).hexdigest()
    now = time.time()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM throttle WHERE expires < ?", (now,))
        row = conn.execute("SELECT count FROM throttle WHERE bucket=?", (key,)).fetchone()
        if row and row["count"] >= maximum:
            return False
        if row:
            conn.execute("UPDATE throttle SET count=count+1 WHERE bucket=?", (key,))
        else:
            conn.execute("INSERT INTO throttle VALUES(?,1,?)", (key, now + seconds))
    return True


def mail_ready():
    return all(os.environ.get(k, "").strip() for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"))


def send_code(email, code, purpose):
    if not mail_ready():
        raise RuntimeError("SMTP indisponível")
    message = EmailMessage()
    message["From"] = os.environ["MAIL_FROM"]
    message["To"] = email
    message["Subject"] = "CodeStart — " + ("confirme seu cadastro" if purpose == "verify" else "recupere sua senha")
    message.set_content(
        f"Seu código CodeStart é: {code}\n\n"
        "Ele vence em 15 minutos e só pode ser usado uma vez.\n"
        "Digite-o na tela em que você solicitou o código.\n"
        "Se não foi você, ignore esta mensagem e não compartilhe o código."
    )
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    context = ssl.create_default_context()
    if os.environ.get("SMTP_SECURITY", "starttls") == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            server.send_message(message)


def digest(challenge_id, code):
    return hmac.new(current_app.secret_key.encode(), f"{challenge_id}:{code}".encode(), hashlib.sha256).hexdigest()


def issue(user, email, purpose, payload=None):
    cid, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1000000):06d}"
    with db() as conn:
        conn.execute("DELETE FROM challenges WHERE expires < ?", (time.time(),))
        conn.execute("INSERT INTO challenges(id,user_id,purpose,digest,expires,payload) VALUES(?,?,?,?,?,?)",
                     (cid, user, purpose, digest(cid, code), time.time() + 900, json.dumps(payload or {})))
    try:
        send_code(email, code, purpose)
    except Exception as exc:
        with db() as conn:
            conn.execute("DELETE FROM challenges WHERE id=?", (cid,))
        current_app.logger.warning("Falha de envio SMTP: %s", type(exc).__name__)
        raise RuntimeError("Não foi possível enviar o e-mail. Tente novamente mais tarde.") from None
    return cid


def consume(cid, code, purpose, password=None):
    if not isinstance(cid, str) or not re.fullmatch(r"\d{6}", code):
        return False
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM challenges WHERE id=? AND purpose=?", (cid, purpose)).fetchone()
        if not row or row["expires"] < time.time() or row["attempts"] >= 5:
            return False
        if not hmac.compare_digest(row["digest"], digest(cid, code)):
            conn.execute("UPDATE challenges SET attempts=attempts+1 WHERE id=?", (cid,))
            return False
        if purpose == "verify":
            payload = json.loads(row["payload"])
            conn.execute("UPDATE accounts SET verified=1,name=?,password_hash=?,session_version=session_version+1 WHERE id=?",
                         (payload["name"], payload["password_hash"], row["user_id"]))
        else:
            conn.execute("UPDATE accounts SET password_hash=?,session_version=session_version+1 WHERE id=?",
                         (password, row["user_id"]))
        conn.execute("DELETE FROM challenges WHERE user_id=?", (row["user_id"],))
    return True


@auth.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = text_field("email").lower()
        password = request.form.get("password", "")
        if not allow("login-ip:" + str(request.remote_addr), 40, 900) or not allow("login:" + email, 10, 900):
            error = "Muitas tentativas. Aguarde 15 minutos."
        else:
            with db() as conn:
                row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
            valid = check_password_hash(row["password_hash"] if row else DUMMY_HASH, password[:128])
            if row and valid and row["verified"]:
                session.clear()
                session.update(uid=row["id"], version=row["session_version"], csrf=secrets.token_urlsafe(32))
                session.permanent = True
                return redirect("/")
            error = "E-mail ou senha inválidos, ou cadastro ainda não confirmado."
    return render_template("auth.html", mode="login", error=error)


@auth.route("/cadastro", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        try:
            email, password, name = email_field(), password_field(), text_field("name")
            if not 2 <= len(name) <= 80:
                raise ValueError("Digite um nome entre 2 e 80 caracteres.")
            if not mail_ready():
                raise ValueError("O envio de e-mails ainda não foi configurado pelo administrador.")
            if not allow("email:" + email, 6, 3600) or not allow("mail-ip:" + str(request.remote_addr), 20, 3600):
                raise ValueError("Limite de solicitações atingido. Tente novamente em uma hora.")
            hashed = generate_password_hash(password)
            with db() as conn:
                conn.execute("INSERT OR IGNORE INTO accounts(name,email,password_hash) VALUES(?,?,?)",
                             (name, email, DUMMY_HASH))
                row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
            if row["verified"]:
                session["verify_challenge"] = secrets.token_urlsafe(32)
            else:
                session["verify_challenge"] = issue(row["id"], email, "verify", {"name": name, "password_hash": hashed})
            return redirect(url_for("auth.verify"))
        except (ValueError, RuntimeError) as exc:
            error = str(exc)
    return render_template("auth.html", mode="register", error=error)


@auth.route("/confirmar-email", methods=["GET", "POST"])
def verify():
    error = None
    if request.method == "POST":
        if consume(session.get("verify_challenge"), text_field("code"), "verify"):
            session.pop("verify_challenge", None)
            return redirect(url_for("auth.login", confirmed="1"))
        error = "Código inválido, expirado ou sem tentativas restantes. Faça o cadastro novamente para receber outro."
    return render_template("auth.html", mode="verify", error=error, notice=GENERIC)


@auth.route("/esqueci-senha", methods=["GET", "POST"])
def forgot():
    error = None
    if request.method == "POST":
        try:
            email = email_field()
            if not mail_ready():
                raise ValueError("O envio de e-mails ainda não foi configurado pelo administrador.")
            if not allow("email:" + email, 6, 3600) or not allow("mail-ip:" + str(request.remote_addr), 20, 3600):
                raise ValueError("Limite de solicitações atingido. Tente novamente em uma hora.")
            with db() as conn:
                row = conn.execute("SELECT * FROM accounts WHERE email=?", (email,)).fetchone()
            if row and row["verified"]:
                session["reset_challenge"] = issue(row["id"], email, "reset")
            else:
                session["reset_challenge"] = None
            session["reset_notice"] = GENERIC
            return redirect(url_for("auth.reset"))
        except (ValueError, RuntimeError) as exc:
            error = str(exc)
    return render_template("auth.html", mode="forgot", error=error, notice=GENERIC)


@auth.route("/redefinir-senha", methods=["GET", "POST"])
def reset():
    error = None
    notice = session.pop("reset_notice", None)
    if request.method == "POST":
        try:
            password = password_field()
            hashed = generate_password_hash(password)
            if consume(session.get("reset_challenge"), text_field("code"), "reset", hashed):
                session.pop("reset_challenge", None)
                session.clear()
                return redirect(url_for("auth.login", reset="1"))
            error = "Código inválido, expirado ou sem tentativas restantes."
        except ValueError as exc:
            error = str(exc)
    return render_template("auth.html", mode="reset", error=error, notice=notice or GENERIC)


@auth.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def save_trail(trail: dict) -> None:
    """Persiste a trilha gerada no usuário logado."""
    uid = session.get("uid")
    if not uid:
        return
    try:
        payload = json.dumps(trail, ensure_ascii=False)
    except (TypeError, ValueError):
        return
    with db() as conn:
        conn.execute("UPDATE accounts SET trail=? WHERE id=?", (payload, uid))