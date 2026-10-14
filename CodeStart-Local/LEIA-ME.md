# CodeStart — IA local sem chave
Esta cópia usa Ollama e qwen2.5:1.5b, sem chamadas pagas à OpenAI.
A chave OPENAI_API_KEY que você já salvou não é usada por padrão.

## Abrir no Codespaces
1. Extraia o ZIP. Abra a pasta CodeStart-Local no Codespaces.
2. Instale Ollama uma vez, com o instalador oficial:
   curl -fsSL https://ollama.com/install.sh -o /tmp/instalar-ollama.sh
   sh /tmp/instalar-ollama.sh
   O instalador pode pedir sudo. Em Codespaces, systemd pode não estar disponível;
   o script INICIAR.sh inicia o processo diretamente.
3. No terminal dentro desta pasta:
   bash INICIAR.sh
4. Espere terminar a instalação das dependências e o download do modelo.
5. Abra a porta 5000 no navegador. Envie uma pergunta curta no Tutor.

O script baixa o modelo na primeira execução e verifica nas seguintes.
O modelo exige espaço em disco e memória. Se faltar memória ou o ambiente
não permitir a instalação, envie o erro; não há garantia de desempenho.
A primeira resposta pode demorar; o tempo máximo no aplicativo é 3 minutos.
O modelo é pequeno: português, raciocínio e código podem ser inferiores aos
modelos grandes. Confira as respostas antes de usar.
Não há cobrança de API por pergunta, mas o Codespaces mantém seus próprios
limites de processamento, armazenamento e eventuais cobranças da conta.
Não publique a porta 11434. A integração acessa apenas 127.0.0.1.
As conversas ficam no navegador e são enviadas ao Ollama dentro do Codespaces.

Para voltar à busca no material sem iniciar modelo:
AI_PROVIDER=local python app.py

Validação: sintaxe e testes simulados. Não foi feito download nem teste real
do modelo neste ambiente. O teste real precisa ocorrer no seu Codespaces.

Fontes:
https://docs.ollama.com/linux
https://docs.ollama.com/api/chat
https://ollama.com/library/qwen2.5:1.5b
