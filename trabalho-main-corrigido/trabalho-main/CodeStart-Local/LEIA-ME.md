# CodeStart

Plataforma de estudos de programação (Flask + HTML/JS).

## Como rodar (qualquer computador ou Codespaces)
```bash
cd CodeStart-Local
pip install -r requirements.txt
python app.py
```
Abra http://localhost:5000 (no Codespaces, abra a porta 5000).
Não precisa configurar nada para o site funcionar.

## Como funciona o acesso
- **Sem login** dá para usar o site todo: catálogo, trilha, editor, jogos, projetos, dicionário e tutor.
- **Os cursos (abrir as aulas) exigem login.** Visitantes veem o catálogo, e ao clicar em "Começar curso" aparece o convite para entrar ou criar conta.
- O conteúdo das aulas só é enviado pelo servidor para quem está logado.

## Código de verificação por e-mail
- **Sem configurar nada (modo de teste):** ao criar a conta, o código de 6 dígitos aparece na própria tela de confirmação e também no terminal onde o `python app.py` está rodando. A recuperação de senha imprime o código só no terminal.
- **E-mail de verdade:** copie `.env.example` para `.env` (na mesma pasta do `app.py`) e preencha as linhas `SMTP_*` e `MAIL_FROM`. Com SMTP configurado, o modo de teste desliga sozinho e o código passa a ir só por e-mail.
  Gmail: ative a verificação em duas etapas e crie uma *senha de app* em https://myaccount.google.com/apppasswords. Use essa senha em `SMTP_PASSWORD`.
- Em um site publicado, defina `DEV_SHOW_CODE=0` e configure o SMTP.

## Tutor
- **Padrão (`AI_PROVIDER=auto`):** com `GROQ_API_KEY` no `.env` (chave gratuita em https://console.groq.com/keys) as respostas são geradas por IA. Sem chave, o tutor responde buscando no material dos cursos.
- Se a IA falhar (sem internet, limite de uso...), o tutor cai automaticamente para a busca no material em vez de mostrar erro. Para desligar isso: `TUTOR_FALLBACK=0`.
- Opções avançadas: `AI_PROVIDER=openai` (usa `OPENAI_API_KEY`) ou `AI_PROVIDER=ollama` (IA local; veja `INICIAR.sh`, precisa do Ollama instalado).

## Testes
```bash
python test_app.py && python test_tutor_ai.py && python test_local.py
```

## Segredos e dados locais
`.env`, `instance/` (contas e chave de sessão), `*.sqlite3` e `.codestart-secret` estão no `.gitignore`. Não envie esses arquivos para o GitHub.
