# 03: Navegação e metadados da Biblioteca

**What to build:** O usuário navega pela Biblioteca com busca e ordenação, vê a Capa de cada Faixa (ou um placeholder de gatinho quando falta arte), corrige metadados errados direto no app sem alterar os arquivos originais, e limpa ou reprocessa Itens não reconhecidos.

**Blocked by:** 02: Importação em lote & Biblioteca

**Status:** ready-for-agent

- [ ] Busca por título, artista ou álbum filtra a lista em tempo real
- [ ] Ordenação por título, artista, duração e data de importação
- [ ] A Capa embutida é exibida quando existe; um placeholder de gatinho (cor determinística a partir do nome do álbum) aparece quando falta
- [ ] Título, artista, álbum e Capa podem ser editados no app; a edição vira override no SQLite e o arquivo de áudio permanece intacto
- [ ] Itens não reconhecidos podem ser removidos e reprocessados
- [ ] Testes no seam da API cobrem: busca/ordenação e edição de metadados criando override sem alterar o arquivo
