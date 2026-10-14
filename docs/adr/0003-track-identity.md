# Identidade da Faixa é o hash do conteúdo

Uma **Faixa** é identificada pelo hash do conteúdo do arquivo, não pelo nome. Duplicatas são detectadas por hash e ignoradas. Edições de metadados feitas no app (título/artista/álbum/capa) são **overrides guardados no SQLite**; os arquivos de áudio nunca são reescritos.

Alternativas consideradas: identidade por nome de arquivo — rejeitada porque nome mente e gera duplicatas; escrever as edições de volta nas tags ID3 — adiada porque reescrever os arquivos do usuário é irreversível e desnecessário para o caso local de usuário único.
