# Musicat

Aplicativo multiusuário auto-hospedado para importar, organizar e tocar músicas baixadas, com compartilhamento de Playlists e um palco de gatinhos que dançam sincronizados ao áudio.

## Language

**Faixa** (Track):
Uma música importada, identificada pelo hash do conteúdo do arquivo.
_Avoid_: música (como a entidade), arquivo, song

**Biblioteca**:
O conjunto de todas as Faixas importadas e guardadas no servidor.
_Avoid_: coleção, acervo, library

**Usuário**:
Uma conta autenticada pelo Supabase. A identidade é o `sub` do token, não o e-mail.
_Avoid_: conta (como identidade), cliente, pessoa

**Sessão**:
O token emitido pelo Supabase que prova a identidade de um Usuário; enviado como Bearer nas chamadas da API.
_Avoid_: login, cookie

**Dono**:
O Usuário que criou uma Playlist. Tem controle total sobre ela: renomear, apagar, mudar visibilidade, convidar e editar Faixas.
_Avoid_: proprietário, admin, criador

**Convidado**:
Um Usuário convidado pelo Dono para uma Playlist Privada. Pode ver, ouvir e editar as Faixas dela.
_Avoid_: colaborador, membro, participante

**Playlist Pública**:
Uma Playlist que qualquer Usuário autenticado pode ver, ouvir e cujas Faixas pode editar. Só o Dono renomeia, apaga, muda a visibilidade e convida.
_Avoid_: playlist aberta, playlist compartilhada

**Playlist Privada**:
Uma Playlist visível e editável apenas pelo Dono e pelos Convidados.
_Avoid_: playlist fechada, playlist pessoal

**Playlist**:
Uma sequência ordenada e nomeada de Faixas, criada pelo Usuário ou gerada, com visibilidade Pública ou Privada.
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
