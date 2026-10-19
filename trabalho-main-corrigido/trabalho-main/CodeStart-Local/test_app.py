import os
os.environ["AI_PROVIDER"] = "local"
os.environ["APP_DATA_DIR"] = __import__("tempfile").mkdtemp()
for _k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"):
    os.environ.pop(_k, None)
import re
import unittest
from app import app


def csrf_client():
    """Cliente de teste que já tem sessão e token CSRF (como o navegador, via <meta>)."""
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
    client.csrf = {"X-CSRF-Token": token}
    return client


def create_account(client, email="aluno@exemplo.com", name="Maria Souza", password="uma-senha-bem-longa"):
    page = client.get("/cadastro").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post("/cadastro", data={"csrf_token": token, "name": name, "email": email,
                                   "password": password, "confirm_password": password})
    page = client.get("/confirmar-email").get_data(as_text=True)
    code = re.search(r"<strong>(\d{6})</strong>", page).group(1)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    r = client.post("/confirmar-email", data={"csrf_token": token, "code": code})
    return r, password


class CodeStartTests(unittest.TestCase):
    def setUp(self):
        self.client = csrf_client()

    def test_site_is_public(self):
        for path in ['/', '/static/upgrade.js', '/static/upgrade.css', '/static/auth.css', '/login', '/cadastro']:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200, path)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Entrar", html)
        self.assertIn('id="login-gate"', html)
        self.assertIn("loggedIn: false", html)

    def test_visitor_catalog_hides_lesson_content(self):
        data = self.client.get('/api/catalogo').get_json()
        self.assertEqual(data['course_count'], 11)
        self.assertEqual(data['lesson_count'], 639)
        lesson = data['courses'][0]['lessons'][0]
        self.assertTrue(lesson['title'])
        self.assertEqual(lesson['body'], "")
        self.assertEqual(lesson['theory'], [])

    def test_logged_user_gets_full_lessons_and_gate_opens(self):
        client = csrf_client()
        r, password = create_account(client)
        self.assertEqual(r.status_code, 302)
        page = client.get("/login?confirmed=1").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        r = client.post("/login", data={"csrf_token": token, "email": "aluno@exemplo.com", "password": password,
                                        "next": "/#cursos"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/#cursos"))
        html = client.get("/").get_data(as_text=True)
        self.assertIn("loggedIn: true", html)
        self.assertNotIn('id="login-gate"', html)
        client.csrf = {"X-CSRF-Token": re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)}
        lesson = client.get('/api/catalogo').get_json()['courses'][0]['lessons'][0]
        self.assertTrue(lesson['body'])

    def test_wrong_password_and_open_redirect(self):
        page = self.client.get("/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        r = self.client.post("/login", data={"csrf_token": token, "email": "x@y.com", "password": "errada",
                                             "next": "https://evil.example"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("E-mail ou senha inválidos", r.get_data(as_text=True))
        self.assertNotIn("evil.example", r.get_data(as_text=True))

    def test_post_without_csrf_is_rejected(self):
        r = app.test_client().post('/api/tutor', json={'pergunta': 'listas Python'})
        self.assertEqual(r.status_code, 400)

    def test_combined_trail_no_duplicates(self):
        result = self.client.post('/api/trilha', json={'objetivos': ['python']}, headers=self.client.csrf).get_json()
        self.assertTrue(result['success'])
        self.assertEqual(len(result['course_ids']), len(set(result['course_ids'])))
        self.assertEqual(result['courses'][0]['lessons'][0]['body'], "")

    def test_bad_payloads(self):
        for payload in [[], 'texto', 12]:
            self.assertEqual(self.client.post('/api/trilha', json=payload, headers=self.client.csrf).status_code, 400)

    def test_python_imports_and_error(self):
        h = self.client.csrf
        result = self.client.post('/api/editor/python/check', json={'code': 'from flask import Flask\nimport os, json'}, headers=h).get_json()
        self.assertEqual(result['imports'], ['flask', 'os', 'json'])
        result = self.client.post('/api/editor/python/check', json={'code': 'def oi('}, headers=h).get_json()
        self.assertFalse(result['valid'])

    def test_java_strings_comments_and_main(self):
        h = self.client.csrf
        code = 'public class Main { public static void main(String[] args) { System.out.println("https://exemplo.com/{"); } }'
        result = self.client.post('/api/editor/java/check', json={'code': code}, headers=h).get_json()
        self.assertTrue(result['valid'])
        self.assertTrue(result['has_main'])
        result = self.client.post('/api/editor/java/check', json={'code': 'public class Main { ('}, headers=h).get_json()
        self.assertFalse(result['valid'])

    def test_sql_readonly(self):
        h = self.client.csrf
        result = self.client.post('/api/editor/sql', json={'query': 'SELECT * FROM usuarios WHERE ativo = 1'}, headers=h).get_json()
        self.assertEqual(result['count'], 3)
        for query in ['DELETE FROM usuarios', 'WITH ids AS (SELECT 1) DELETE FROM usuarios']:
            self.assertEqual(self.client.post('/api/editor/sql', json={'query': query}, headers=h).status_code, 400)

    def test_sql_timeout(self):
        query = 'WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT sum(n) FROM x'
        self.assertEqual(self.client.post('/api/editor/sql', json={'query': query}, headers=self.client.csrf).status_code, 400)

    def test_json_valid_and_invalid(self):
        for code, valid in [('{"a":1}', True), ('{', False)]:
            self.assertEqual(self.client.post('/api/editor/json/check', json={'code': code}, headers=self.client.csrf).get_json()['valid'], valid)

    def test_tutor_works_for_visitors_without_any_key(self):
        h = self.client.csrf
        self.assertEqual(self.client.post('/api/tutor', json={'pergunta': ''}, headers=h).status_code, 400)
        result = self.client.post('/api/tutor', json={'pergunta': 'Como funcionam as listas em Python?'}, headers=h).get_json()
        self.assertTrue(result['success'])
        self.assertTrue(result['answer'])


class RegistrationWithoutSMTP(unittest.TestCase):
    def test_code_is_shown_and_account_confirmed(self):
        client = csrf_client()
        r, _ = create_account(client, email="novo@exemplo.com")
        self.assertEqual(r.status_code, 302)
        self.assertIn("confirmed=1", r.headers["Location"])

    def test_wrong_code_rejected(self):
        client = csrf_client()
        page = client.get("/cadastro").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        client.post("/cadastro", data={"csrf_token": token, "name": "Joana", "email": "joana@exemplo.com",
                                       "password": "outra-senha-longa", "confirm_password": "outra-senha-longa"})
        page = client.get("/confirmar-email").get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        r = client.post("/confirmar-email", data={"csrf_token": token, "code": "000000"})
        self.assertIn("Código inválido", r.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
