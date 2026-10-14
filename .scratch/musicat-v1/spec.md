# Spec: Musicat v1 — importar, tocar e dançar

Status: ready-for-agent

## Problem Statement

O usuário baixa arquivos de música para o computador e eles ficam espalhados numa pasta de downloads, sem organização, sem forma fácil de tocar em sequência, e sem nenhum prazer visual. Ele quer um app local, bonito e fofo, onde arrasta os arquivos baixados, os vê virar uma biblioteca, monta playlists na ordem que quiser (ou deixa no aleatório) e, enquanto a música toca, gatinhos dançam no ritmo.

## Solution

O **Musicat** é um web app local de usuário único. Um backend Python (FastAPI) recebe os arquivos arrastados para o navegador, copia-os para uma biblioteca gerenciada no servidor e os guarda num banco SQLite, e faz stream do áudio de volta ao navegador. Todo o front-end é vanilla JS/HTML/CSS servido pelo próprio backend na `localhost`. O áudio toca no navegador via Web Audio API, e a energia e a batida do áudio, extraídas com um `AnalyserNode`, dirigem um **Palco** de três **Gatinhos** em SVG animados, com um overlay de partículas. O usuário monta **Playlists** ordenadas por drag-and-drop, alterna o **Modo Aleatório** e controla uma **Fila** com repetição. Tudo em PT-BR, com tema escuro aconchegante.

## User Stories

### Importação
1. Como usuário, quero arrastar um ou vários arquivos de música para dentro do app, para importá-los de uma vez.
2. Como usuário, quero arrastar uma pasta inteira, para importar tudo que está dentro.
3. Como usuário, quero ver uma barra de progresso durante o upload em lote, para saber que está acontecendo.
4. Como usuário, quero que o app aceite mp3, flac, m4a/aac, ogg/opus e wav, para não precisar converter nada.
5. Como usuário, quero que arquivos que o navegador não toca sejam recusados com aviso, em vez de entrarem quebrados.
6. Como usuário, quero que os arquivos importados sejam copiados e guardados no servidor, para não depender de mover os originais.
7. Como usuário, quero continuar ouvindo música enquanto um upload acontece, para não ser interrompido.

### Biblioteca e metadados
8. Como usuário, quero ver todas as Faixas importadas numa lista, para ter a biblioteca num lugar só.
9. Como usuário, quero buscar por título, artista ou álbum, para achar uma Faixa rápido.
10. Como usuário, quero ordenar por título, artista, duração ou data de importação, para navegar do meu jeito.
11. Como usuário, quero ver título, artista, álbum, duração e Capa de cada Faixa lidos das tags do arquivo, para reconhecê-las.
12. Como usuário, quero corrigir título, artista, álbum e Capa dentro do app, para arrumar tags erradas.
13. Como usuário, quero que minhas correções não alterem os arquivos originais, para não estragar minha coleção.
14. Como usuário, quero que uma Capa placeholder de gatinho apareça quando faltar arte, para a UI ficar bonita mesmo sem imagem.
15. Como usuário, quero que uma mesma música arrastada duas vezes não vire duplicata, para a biblioteca ficar limpa.
16. Como usuário, quero que um arquivo inválido vire um "Item não reconhecido" visível, para saber o que falhou sem perder o lote.
17. Como usuário, quero remover ou reprocessar um Item não reconhecido, para limpar a bagunça.

### Reprodução
18. Como usuário, quero tocar e pausar uma Faixa, para ouvir a música.
19. Como usuário, quero avançar e voltar de Faixa, para navegar na Fila.
20. Como usuário, quero arrastar a barra de progresso, para começar do ponto que eu quiser.
21. Como usuário, quero ajustar o volume, para ouvir no nível que eu gosto.
22. Como usuário, quero repetir desligado, tudo ou uma Faixa, para controlar a repetição.
23. Como usuário, quero ligar e desligar o Modo Aleatório, para ouvir embaralhado sem perder a ordem salva.
24. Como usuário, quero que a próxima Faixa toque automaticamente, para a música não parar sozinha.
25. Como usuário, quero ver a Fila atual, para saber o que vem depois.
26. Como usuário, quero que, ao dar play numa Faixa de uma Playlist, a Fila seja a Playlist inteira a partir dela, respeitando aleatório e repetição.
27. Como usuário, quero que, ao recarregar a página, a Fila, a Faixa atual, a posição e o volume sejam lembrados, para continuar de onde parei.

### Playlists
28. Como usuário, quero criar uma Playlist com nome, para organizar minha música.
29. Como usuário, quero adicionar e remover Faixas de uma Playlist, para montar minha seleção.
30. Como usuário, quero reordenar as Faixas de uma Playlist por drag-and-drop, para definir a sequência exata.
31. Como usuário, quero renomear e apagar uma Playlist, para manter tudo organizado.
32. Como usuário, quero gerar uma Playlist aleatória com filtros opcionais (artista, formato) e um tamanho N, para descobrir combinações novas.
33. Como usuário, quero que a Playlist aleatória gerada seja salva como uma Playlist normal, para poder editá-la e reouvê-la.

### Palco e Gatinhos
34. Como usuário, quero ver três Gatinhos dançando no Palco enquanto a música toca, para o app ser fofo e vivo.
35. Como usuário, quero que os Gatinhos reajam à batida e à energia da música, para sentirem "sincronizados".
36. Como usuário, quero que graves, médios e agudos movam partes diferentes, para a dança ter variedade.
37. Como usuário, quero ver brilhos/partículas soltando no ritmo, para a festa visual.
38. Como usuário, quero que cada Gatinho tenha uma personalidade distinta, para o Palco não ser repetitivo.
39. Como usuário, quero que o Palco reflita o estado do player (toco/pausado), para os Gatinhos pararem quando a música para.

### Interface e início
40. Como usuário, quero uma interface em PT-BR, para entender tudo sem esforço.
41. Como usuário, quero um tema escuro aconchegante com acentos pastel, para o app ser agradável de olhar.
42. Como usuário, quero tocar a partir de um comando único que abre o navegador, para parecer um app de verdade.
43. Como usuário, quero que os dados (arquivos e banco) fiquem numa pasta `data/` que eu possa inspecionar e apagar, para ter controle e fazer backup.

## Implementation Decisions

**Arquitetura** (ADR-0001): backend FastAPI + uvicorn serve o front vanilla JS/HTML/CSS e faz stream do áudio; reprodução e análise de batida no navegador via Web Audio API (`AnalyserNode`); Python não decodifica nem toca áudio. Single-user, sem auth. Porta configurável, escolhida automaticamente se a padrão estiver ocupada. Entrypoint `python -m musicat` sobe o servidor e abre o navegador.

**Forma do projeto**: `src/musicat/` com `app.py` (rotas FastAPI), pacote `library/` (importação, hash, metadados, acesso ao SQLite), `models.py` (Faixa, Playlist, Item não reconhecido) e `static/` (front). Pasta `data/` na raiz do projeto para os arquivos e o `musicat.db`, ignorada pelo git, configurável por variável de ambiente. Dependências: `fastapi`, `uvicorn`, `python-multipart`, `mutagen`; dev: `pytest`.

**Identidade da Faixa** (ADR-0003): a identidade é o hash do conteúdo do arquivo, não o nome. Duplicatas são detectadas por hash e ignoradas (a API responde informando "já está na Biblioteca"). Edições de metadados são overrides guardados no SQLite; os arquivos de áudio nunca são reescritos.

**Metadados**: lidos das tags do arquivo (título, artista, álbum, duração, formato, Capa) via mutagen; `ffmpeg`/`ffprobe` como reserva quando as tags faltarem. Formatos aceitos: mp3, flac, m4a/aac, ogg/opus, wav. Formatos não suportados pelo navegador são recusados com aviso, não transcode.

**Modelo de Playlist** (ADR-0002): uma Playlist é sempre uma sequência ordenada e nomeada de Faixas. O Modo Aleatório é um modo de reprodução que embaralha a Fila sem alterar a ordem salva. "Gerar playlist aleatória" sorteia Faixas (filtros opcionais por artista/formato e tamanho N) e grava o resultado como uma Playlist normal.

**Fila e estado de reprodução**: a Fila é a ordem atual de reprodução, distinta das Playlists salvas. Ao dar play numa Faixa dentro de uma Playlist, a Fila passa a ser a Playlist inteira a partir dela, respeitando Modo Aleatório e repetição. A Fila, a Faixa atual, a posição e o volume são persistidos no SQLite e restaurados ao recarregar.

**Contratos de API** (seam de teste, exercido por HTTP): endpoints para upload em lote (multipart, múltiplos arquivos, com status por arquivo — importado / duplicata / não reconhecido), listagem e busca/ordenação da Biblioteca, edição de metadados da Faixa, CRUD de Playlists (criar, renomear, apagar, adicionar/remover/reordenar Faixas), geração de Playlist aleatória (filtros + tamanho), leitura/gravação do estado do player (Fila, Faixa atual, posição, volume), e stream do áudio de uma Faixa (com suporte a requisições de intervalo para o seek). Erros retornam status HTTP e uma mensagem legível em PT-BR.

**Upload em lote**: multipart com múltiplos arquivos; progresso no front; sem limite rígido de tamanho (aviso acima de um limiar alto); não bloqueia a reprodução.

**Palco e Gatinhos**: três Gatinhos desenhados em SVG, animados por JS (transform/CSS), com um overlay de Canvas 2D para brilhos/partículas. O sinal vem de um `AnalyserNode` do navegador decomposto em bandas (grave/médio/agudo) que modulam intensidade e velocidade, mais detecção de batida (onset) que dispara pulos. Cada Gatinho tem uma personalidade distinta mapeada a bandas diferentes. A Capa placeholder é um gatinho SVG gerado com cor determinística a partir do nome do álbum.

**Interface**: PT-BR, tema escuro aconchegante com acentos pastel; Palco grande no topo, Capa e metadados da Faixa ao lado, waveform reativa, Fila/Playlist embaixo.

**Repositório**: inicializar git com `.gitignore` ignorando `data/`, `.venv/`, `__pycache__/`.

## Testing Decisions

- **Um único seam: a API HTTP do FastAPI**, exercitada com o `TestClient`, contra um diretório `data/` temporário isolado por teste. Nenhum seam no módulo `library` separado — ele é exercido através da API.
- **Bom teste aqui** verifica comportamento externo observável (respostas HTTP, estado da Biblioteca/Playlists/estado do player resultante de uma sequência de chamadas), não detalhes de implementação. Nada de testar funções helper privadas.
- **Cobertura por comportamento**:
  - Upload em lote: um arquivo válido vira Faixa na Biblioteca; duas submissões do mesmo conteúdo resultam em uma única Faixa (duplicata relatada); arquivo inválido vira Item não reconhecido sem derrubar o lote.
  - Metadados: tags lidas na importação; edição cria override sem alterar o arquivo.
  - Playlist: criar, adicionar/remover/reordenar Faixas, renomear, apagar; a ordem persistida reflete a ordem enviada.
  - Playlist aleatória: com filtro e tamanho N respeitados; resultado salvo como Playlist normal.
  - Estado do player: ler/gravar Fila, Faixa atual, posição e volume; round-trip preserva o estado.
  - Stream: retorna os bytes da Faixa; Faixa inexistente retorna erro adequado.
- **Prior art**: não há testes no repo ainda; este será o primeiro conjunto, estabelecendo o padrão de fixtures de áudio (arquivos de áudio mínimos gerados em teste) e de `data/` temporário.
- **Fora do teste automatizado**: todo o front-end (Palco, Gatinhos, animação, UI) — validação manual no navegador.

## Out of Scope

- Multiusuário, login, contas, autenticação.
- Escrever edições de metadados de volta nas tags ID3 dos arquivos.
- Transcodificação de áudio (converter formatos).
- Testes automatizados de front-end.
- Empacotamento como app desktop (janela nativa) — apenas web app local.
- Letras de música, visualizações além dos Gatinhos, integração com serviços de streaming.
- Sincronização entre múltiplos navegadores/abas.
- Suporte a dispositivos móveis.

## Further Notes

- Os formatos aceitos são os que o navegador toca nativamente; manter essa lista alinhada com suporte dos navegadores-alvo.
- O limiar de "arquivo gigante" para o aviso de upload fica como constante configurável.
- A `data/` deve funcionar igual sendo vazia (primeiro uso) ou já povoada.
