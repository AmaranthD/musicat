# Playlist é uma sequência ordenada; Shuffle é modo de reprodução

Uma **Playlist** é sempre uma sequência ordenada e nomeada de Faixas. "Aleatório" não é um tipo de Playlist: é um **Modo Aleatório**, um modo de reprodução que embaralha a Fila sem alterar a ordem salva. A ação "gerar playlist aleatória" sorteia Faixas (com filtros e tamanho opcionais) e **grava o resultado como uma Playlist normal**, congelando aquela ordem.

Alternativas consideradas: tratar "aleatória" como um tipo distinto de Playlist — rejeitada porque duplica o conceito de Playlist e complica o modelo de dados; e shuffle que reordena permanentemente — rejeitada porque destrói a sequência que o usuário estabeleceu.
