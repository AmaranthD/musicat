# 02: Importação em lote & Biblioteca

**What to build:** O usuário arrasta um ou vários arquivos de música para dentro do app, vê uma barra de progresso, e as Faixas importadas aparecem na Biblioteca com título, artista, álbum e duração lidos das tags. Músicas repetidas não duplicam; arquivos inválidos viram um Item não reconhecido visível, sem derrubar o restante do lote.

**Blocked by:** 01: Walking skeleton

**Status:** ready-for-agent

- [ ] Arrastar múltiplos arquivos (ou uma pasta) envia todos numa só operação e mostra progresso
- [ ] Cada arquivo válido é copiado para a Biblioteca gerenciada no servidor e vira uma Faixa no SQLite
- [ ] A Faixa é identificada pelo hash do conteúdo; reenviar o mesmo conteúdo não cria duplicata e é relatado como "já está na Biblioteca"
- [ ] Os formatos aceitos são mp3, flac, m4a/aac, ogg/opus e wav; outros são recusados com aviso
- [ ] Título, artista, álbum e duração são lidos das tags do arquivo
- [ ] Um arquivo corrompido ou sem áudio legível vira um Item não reconhecido visível, e o resto do lote é importado normalmente
- [ ] A Biblioteca aparece numa lista na tela, atualizada após o upload
- [ ] Testes no seam da API cobrem: import válido, dedupe por hash, e arquivo inválido sem derrubar o lote
