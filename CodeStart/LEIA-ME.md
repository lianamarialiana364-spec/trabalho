# Ativar a tutora com IA
Arquivos alterados: app.py, requirements.txt, templates/index.html e static/upgrade.js.
O restante do projeto foi preservado. Copie cada seção para o arquivo indicado.

1. Crie uma chave em https://platform.openai.com/api-keys e configure a cobrança da API.
2. No Render, abra o serviço > Environment > Add Environment Variable:
   OPENAI_API_KEY = sua chave privada
   OPENAI_MODEL = gpt-4.1-mini
3. Salve e publique. Nunca coloque a chave nos arquivos do GitHub ou no HTML.
4. Para serviço Python 3, Build Command: pip install -r requirements.txt
   Start Command: gunicorn --workers 1 --threads 4 --timeout 60 app:app
5. Envie os arquivos ao GitHub e publique a versão mais recente no Render.
6. Abra Tutor e pergunte: Explique listas em Python.
   O rodapé distingue resposta de IA e busca local.

Sem chave, a busca local continua funcionando. Com chave inválida, falta de créditos
ou indisponibilidade, o chat mostra o erro sem expor a chave.
O tutor envia no máximo quatro trocas anteriores, não envia todo o currículo.
Limites: pergunta de 2.000 caracteres, resposta de 1.000 tokens e 100 tentativas
por hora por processo. Este último limite reinicia com o servidor e NÃO é teto
financeiro nem cota individual. Para vários workers/instâncias, use contador
compartilhado e autenticação antes de ampliar o acesso público.
store=False desativa o armazenamento da resposta para recuperação via API;
isso não promete ausência de registros operacionais do provedor.
A cobrança da API deve ser verificada na sua conta antes de ativar.
A integração não resolve automaticamente o erro anterior de Dockerfile:
esse erro ainda exige o log completo da publicação.

# CodeStart — versão aprimorada

Projeto Flask completo, organizado a partir dos três arquivos enviados. O currículo original foi preservado integralmente: 11 cursos, 639 aulas e 12 projetos.

## Como executar no Codespaces

Extraia o ZIP e abra a pasta `codestart`. No terminal dessa pasta:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abra a porta **5000** na aba Ports/Portas do Codespaces. Não abra `index.html` diretamente: o catálogo completo e os editores Python, Java, SQL e JSON precisam do Flask.

A mesma sequência funciona em um computador com Python 3.10 ou superior. O modo de depuração fica desligado por padrão. Para parar o servidor, pressione Ctrl+C no terminal.

## Arquivos

- `app.py`: rotas Flask, catálogo, trilhas, tutor e validação dos editores.
- `curriculo.json`: currículo completo original, sem alterações de conteúdo.
- `templates/index.html`: interface original com correções e integração das melhorias.
- `static/upgrade.css`: identidade visual, central de estudos, responsividade e acessibilidade.
- `static/upgrade.js`: central, busca, organização, backup, rascunhos e integrações.
- `requirements.txt`: dependência do projeto.
- `test_app.py`: testes de regressão das rotas.

Copie **a pasta completa**. O novo HTML depende dos dois arquivos da pasta `static`.

## O que foi mantido

Início, trilhas personalizadas, catálogo de cursos, aulas e quizzes, exercícios de prática, editor em seis linguagens, jogos, projetos, dicionário, tutor, dashboard, XP, vidas, conquistas, favoritos, anotações e impressão do registro de estudos.

O currículo JSON permanece idêntico ao arquivo enviado. Os identificadores das aulas e a chave de progresso no navegador também foram mantidos.

## Melhorias

- Visual mais consistente, estado ativo no menu, navegação com histórico e links por seção.
- Central de estudos com busca no conteúdo das 639 aulas, nos títulos e nas anotações.
- Filtros por curso, favoritos, anotações, aulas pendentes e concluídas; resultados paginados.
- Plano semanal com tarefas que podem ser adicionadas, concluídas e excluídas.
- Meta diária e registro dos últimos sete dias; o histórico começa nesta versão e não inventa datas para aulas antigas.
- Cronômetro de foco com duração selecionável, pausa, retomada e contagem de sessões. Recarregar a página reinicia o cronômetro.
- Backup JSON de progresso, notas, favoritos, tarefas e rascunhos; importação com validação e confirmação antes da substituição.
- Exportação das anotações em Markdown.
- Salvamento automático de notas e botão de leitura ampliada.
- Rascunho por linguagem no editor, download do código, Tab para indentar e Ctrl+Enter para executar/validar.
- Execução de JavaScript em worker com limite de três segundos, evitando que um loop infinito trave a interface. Esse modo é voltado a console e lógica; para páginas com DOM, use o editor HTML.
- Tutor conectado ao conteúdo do servidor. Ele faz busca por termos no material didático; não é uma IA generativa nem faz consultas à internet.
- Atalho `/` para buscar aulas, link de pular para o conteúdo, foco de teclado e respeito à preferência por menos animações.

## Correções

- Recuperação do Python enviado com caracteres de formatação Markdown.
- Progresso calculado pela quantidade real de aulas concluídas, inclusive quando estudadas fora de ordem.
- Curso só recebe conclusão quando todas as aulas estiverem marcadas; abrir a última aula não encerra o curso inteiro.
- Recálculo das porcentagens anteriores sem retirar XP já acumulado.
- Correção de expressões do validador Java e dos nomes de imports do Python.
- Consultas SQL somente leitura com interrupção de consultas excessivamente longas e fechamento da conexão.
- Validação de corpo JSON nas rotas e limite de tamanho de requisição.
- Carregamento do currículo em cache, invalidado quando o arquivo muda.
- Aviso quando o catálogo completo não puder ser carregado.
- Impressão focada no registro de estudos, sem imprimir toda a interface.
- O registro não afirma certificação profissional nem conclusão integral de uma trilha sem comprovação.

## Progresso e dependências

O progresso permanece no `localStorage`, sem login e sem sincronização automática entre computadores. No mesmo navegador e endereço do site, a versão reaproveita o progresso antigo. Em outro endereço ou dispositivo, use exportar/importar backup desta versão. A importação substitui os dados atuais somente após a confirmação.

Faça backup antes de limpar os dados do navegador. O salvamento pode ser impedido por falta de espaço ou restrições do navegador; nesse caso a interface exibe um aviso.

Tailwind, ícones e fontes continuam sendo carregados por CDN, como na versão enviada, e precisam de internet. Esta versão não promete funcionamento completamente offline.

Python faz validação de sintaxe, sem executar programas. Java faz checagem estrutural educativa, sem compilador JDK. SQL consulta um banco de exemplo em memória. O preview HTML usa iframe com sandbox. A aplicação não inclui autenticação, banco de alunos ou hospedagem pronta para produção.

## Verificação

Execute:

```bash
python -m unittest test_app.py
```

Durante a preparação foram verificados as rotas Flask, o carregamento do HTML/Jinja, a integridade do currículo e a sintaxe JavaScript. Testes de interação em DOM simulado verificaram inicialização, navegação, busca, favoritos, notas, tarefas, conclusão fora de ordem, backup, rascunhos, cronômetro e redefinição do progresso. Não houve inspeção visual em navegador real neste ambiente.
