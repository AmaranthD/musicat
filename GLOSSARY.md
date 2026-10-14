# Musicat

Aplicativo local de usuário único para importar, organizar e tocar músicas baixadas, com um palco de gatinhos que dançam sincronizados ao áudio.

## Language

**Faixa** (Track):
Uma música importada, identificada pelo hash do conteúdo do arquivo.
_Avoid_: música (como a entidade), arquivo, song

**Biblioteca**:
O conjunto de todas as Faixas importadas e guardadas no servidor.
_Avoid_: coleção, acervo, library

**Playlist**:
Uma sequência ordenada e nomeada de Faixas, criada pelo usuário ou gerada.
_Avoid_: lista, setlist, fila

**Fila** (Queue):
A ordem em que as Faixas vão tocar agora, distinta de qualquer Playlist salva.
_Avoid_: playlist

**Modo Aleatório** (Shuffle):
Modo de reprodução que toca uma sequência em ordem embaralhada sem alterar a ordem salva.
_Avoid_: aleatória (como entidade), random

**Item não reconhecido**:
Um arquivo arrastado que não pôde ser importado como Faixa; permanece visível, removível e reprocessável.
_Avoid_: erro, arquivo inválido

**Capa**:
A imagem de arte associada a uma Faixa ou álbum; quando ausente, usa-se um placeholder.
_Avoid_: artwork, thumbnail, imagem

**Palco**:
A área da interface onde os Gatinhos dançam.
_Avoid_: canvas, visualizador

**Gatinho**:
Um personagem dançante animado cujo movimento é dirigido pela energia e pela batida do áudio em reprodução.
_Avoid_: avatar, mascote
