# 01: Walking skeleton

**What to build:** O usuário roda `python -m musicat`, o servidor sobe, o navegador abre em `localhost` e mostra a casca do app — uma página em PT-BR com o tema escuro aconchejante e o layout base (Palco no topo, Biblioteca/Fila embaixo). O projeto fica estruturado para receber as fatias seguintes.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `python -m musicat` inicia o servidor FastAPI, escolhe a porta (auto se a padrão estiver ocupada) e abre o navegador
- [ ] A página inicial é servida pelo backend e carrega sem erro, com título "Musicat"
- [ ] A UI está em PT-BR e usa o tema escuro aconchejante como base
- [ ] Existe uma pasta `data/` (configurável por variável de ambiente) criada no primeiro uso
- [ ] O repositório git está inicializado com `.gitignore` ignorando `data/`, `.venv/` e `__pycache__/`
- [ ] Existe um teste de fumaça no seam da API (TestClient) provando que o servidor responde
