# 04: Reprodução & Fila

**What to build:** O usuário toca uma Faixa da Biblioteca e ouve a música no navegador, com play/pause, barra de progresso (seek), volume, próxima/anterior e avanço automático para a próxima. A Fila da Biblioteca fica visível, mostrando o que vem depois.

**Blocked by:** 02: Importação em lote & Biblioteca

**Status:** ready-for-agent

- [ ] Tocar e pausar uma Faixa; o áudio toca no navegador via Web Audio API
- [ ] Seek funcional (o servidor entrega o áudio com suporte a requisições de intervalo)
- [ ] Controle de volume
- [ ] Próxima e anterior navegam na Fila
- [ ] Avanço automático para a próxima Faixa ao terminar, sem ação do usuário
- [ ] A Fila atual é visível e reflete a ordem de reprodução
- [ ] O estado visual do player reflete tocar/pausado
- [ ] Teste no seam da API cobre o stream de uma Faixa existente e o erro para Faixa inexistente
