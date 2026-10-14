# 10: Palco — Gatinhos dançando

**What to build:** Enquanto a música toca, três Gatinhos dançam no Palco, cada um com uma personalidade distinta, reagindo à energia e à batida do áudio. Brilhos/partículas soltam no ritmo, e os Gatinhos param quando a música pausa.

**Blocked by:** 04: Reprodução & Fila

**Status:** ready-for-agent

- [ ] Três Gatinhos desenhados em SVG no Palco, visíveis durante a reprodução
- [ ] O sinal vem de um `AnalyserNode`, decomposto em bandas (grave/médio/agudo) que modulam intensidade e velocidade
- [ ] Detecção de batida (onset) dispara pulos
- [ ] Cada Gatinho tem uma personalidade distinta mapeada a bandas diferentes
- [ ] Um overlay de partículas/brilhos reage ao ritmo
- [ ] Pausar a música faz os Gatinhos pararem; retomar faz voltarem a dançar
- [ ] Nenhum arquivo de arte externo é necessário para a dança funcionar
