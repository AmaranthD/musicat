# Autenticação no Supabase, dados no SQLite

Status: aceito. Substitui o aspecto "usuário único" de ADR-0001.

## Contexto

A v1 era um app local de usuário único. Agora há contas, sessões e compartilhamento: Faixas e Playlists podem ser compartilhadas entre Usuários, cada Playlist pode ser Pública ou Privada, e uma Playlist Privada só é acessível a quem o Dono convida.

A restrição do produto é explícita: **Faixas e Playlists continuam no SQLite**. O Supabase não é o banco da aplicação; é só o provedor de identidade.

## Decisão

### Identidade e sessão

- Supabase Auth (e-mail + senha) emite a sessão. A identidade canônica é o `sub` do JWT (UUID), nunca o e-mail.
- O FastAPI valida o JWT localmente contra o JWKS do Supabase (`{url}/auth/v1/.well-known/jwks.json`), conferindo assinatura (`ES256`/`RS256`/`EdDSA`), `exp`, `aud = authenticated` e `iss = {url}/auth/v1`.
- Todo endpoint da API exige sessão. A API aceita `Authorization: Bearer` em qualquer método; aceita cookie **apenas em GET/HEAD**.
- O front-end (supabase-js vendorizado) guarda a sessão, renova o token e envia o Bearer.
- `<audio>` e `background-image` não conseguem mandar Bearer. Por isso `POST /api/auth/session` grava o access token num cookie `HttpOnly`, `SameSite=Lax`, usado só por `/stream` e `/cover` (GET). Escritas continuam exigindo Bearer, o que evita CSRF.

### Modelo de dados no SQLite

- `users(id, email)`: espelho mínimo de quem já entrou, para exibir a conta e resolver convites por e-mail.
- `tracks.owner_id`: a Faixa pertence a quem importou. Duplicatas são por `(owner_id, content_hash)`; o arquivo de áudio continua endereçado pelo hash e pode ser compartilhado fisicamente entre donos.
- `playlists.owner_id` e `playlists.visibility` (`public`/`private`).
- `playlist_invites(playlist_id, user_id, email)`: o convite é resolvido para `user_id` no momento em que é criado. Assim, trocar de e-mail não concede nem remove acesso por engano.
- `player_state.user_id`: Fila, Faixa atual, posição e volume são por Usuário.

### Regras de acesso

- **Faixa**: visível ao Dono e a qualquer Usuário que alcance uma Playlist acessível que a contenha. Editar metadados/capa é só do Dono.
- **Playlist Pública**: qualquer Usuário autenticado vê, ouve e edita a lista de Faixas. Renomear, apagar, mudar visibilidade e convidar continuam exclusivos do Dono.
- **Playlist Privada**: só o Dono e os Convidados veem, ouvem e editam a lista de Faixas. As ações de Dono continuam exclusivas dele.
- Playlist inacessível responde `404` (não revela existência); ação de Dono por quem não é Dono responde `403`.
- Convite só é aceito para e-mail de uma conta que já entrou ao menos uma vez.

### Dados legados

A migração mantém as Faixas/Playlists antigas sem dono. O primeiro Usuário a entrar assume esses registros (`MUSICAT_CLAIM_LEGACY=1`). Em uma instância compartilhada, defina `MUSICAT_CLAIM_LEGACY=0` antes do primeiro login.

## Consequências

- Toda a autorização vive no backend Python. Não há RLS do Supabase a configurar porque não há tabelas da aplicação no Supabase; a chave `service_role` nunca é usada nem exposta.
- O backend precisa de rede para buscar o JWKS na primeira validação (cache de 5 minutos em memória).
- O projeto Supabase precisa de Site URL/Redirect URLs apontando para o app e, para cadastro/recuperação por e-mail, de SMTP configurado.
- O cookie de mídia expira junto com o access token; o front-end o renova a cada `TOKEN_REFRESHED`.

## Alternativas rejeitadas

- **Banco no Supabase com RLS**: violaria a restrição de manter Faixas/Playlists no SQLite.
- **Só cookie de sessão**: CSRF em métodos de escrita.
- **Token na query string do stream**: vaza em logs/histórico e não expira de forma independente.
- **Blob URL para o áudio**: carrega a Faixa inteira na memória e perde o streaming por `Range`.
- **Convite por e-mail sem resolver `user_id`**: ficaria refém de o e-mail do JWT ser reivindicado corretamente para sempre.
