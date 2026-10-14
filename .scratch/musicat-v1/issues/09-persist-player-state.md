# 09: Estado do player persistido

**What to build:** Depois de um F5 no meio da música, o app lembra a Fila, a Faixa atual, a posição e o volume, e retoma de onde o usuário parou.

**Blocked by:** 04: Reprodução & Fila

**Status:** ready-for-agent

- [ ] A Fila, a Faixa atual, a posição e o volume são guardados no SQLite durante a reprodução
- [ ] Recarregar a página restaura a Fila, a Faixa atual, a posição e o volume
- [ ] Teste no seam da API cobre o round-trip de leitura/gravação do estado do player
