# Configuração de autenticação (Supabase)

O Musicat usa o **Supabase Auth** apenas para identidade e sessão. Faixas, Playlists, convites e estado do player continuam no SQLite local (ver ADR-0004).

## 1. Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste se necessário:

```bash
cp .env.example .env
```

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `MUSICAT_SUPABASE_URL` | URL do projeto atual | Endpoint do Supabase Auth/JWKS |
| `MUSICAT_SUPABASE_KEY` | chave publishable atual | Cliente supabase-js no navegador (pública) |
| `MUSICAT_HOST` | `127.0.0.1` | `0.0.0.0` para acessar de outros dispositivos |
| `MUSICAT_PORT` | `8000` | Porta preferida |
| `MUSICAT_CLAIM_LEGACY` | `1` | Primeiro login assume Faixas/Playlists antigas sem dono |

A chave `service_role` **não é usada**. Só a publishable/anon vai ao navegador.

## 2. Painel do Supabase

No projeto `zcvnfxelcgcydopcdayc`:

1. **Authentication → Providers → Email**: habilitado (já está).
2. **Authentication → URL Configuration**:
   - **Site URL**: `http://127.0.0.1:8000` (ou a URL/porta usada).
   - **Redirect URLs**: inclua `http://127.0.0.1:8000/**` e, se usar outra porta/host, a URL correspondente.
3. **Confirmação de e-mail**:
   - O projeto está com `mailer_autoconfirm = false`. O cadastro envia um e-mail de confirmação.
   - Para desenvolvimento rápido, desative **Confirm email** em Authentication → Providers → Email. Com isso o cadastro já devolve sessão.
   - Para produção, mantenha a confirmação ligada e configure **SMTP** em Authentication → Emails. O SMTP padrão do Supabase é limitado e não entrega para qualquer destinatário.
   - Se o SMTP ainda não estiver pronto e você só quer testar, crie usuários manualmente em **Authentication → Users → Add user**, marcando **Auto Confirm**. A senha definida ali serve para o login por e-mail + senha.
4. **Recuperação de senha**: usa o mesmo SMTP e o redirect para `window.location.origin`. A URL precisa estar em **Redirect URLs**.

Sem esses passos, o login por senha funciona, mas cadastro/recuperação por e-mail podem não chegar ou cair numa URL errada.

## 3. Rodar

```bash
pip install -e ".[dev]"
python -m musicat
```

O navegador abre no endereço local. A tela de login aparece antes de qualquer dado.

## 4. Como funciona a sessão

- O front-end usa `supabase-js` (vendorizado em `static/vendor/supabase.js`) para `signInWithPassword`, `signUp`, `resetPasswordForEmail` e renovação automática.
- Cada chamada da API manda `Authorization: Bearer <access_token>`.
- O backend valida o JWT localmente com o JWKS do Supabase (`ES256`) e confere `exp`, `aud` e `iss`.
- `<audio>` e capas não conseguem mandar Bearer. Depois do login, `POST /api/auth/session` grava o token num cookie `HttpOnly`/`SameSite=Lax`; esse cookie só é aceito em GET (stream e capa). Escritas exigem Bearer.
- Logout limpa o cookie e encerra a sessão do Supabase.

## 5. Dados antigos

A migração cria `owner_id` nulo para dados da v1. No primeiro login, se `MUSICAT_CLAIM_LEGACY=1`, esse Usuário assume as Faixas, Playlists e Itens não reconhecidos antigos. Em uma instância que será compartilhada, defina `MUSICAT_CLAIM_LEGACY=0` **antes** do primeiro login e reatribua os dados manualmente se necessário.

## 6. Endpoints novos

| Método | Rota | Acesso |
| --- | --- | --- |
| GET | `/api/auth/config` | público (URL + publishable key) |
| POST | `/api/auth/session` | autenticado; grava cookie de mídia |
| DELETE | `/api/auth/session` | limpa cookie |
| GET | `/api/me` | autenticado |
| GET/POST | `/api/playlists/{id}/invites` | só o Dono |
| DELETE | `/api/playlists/{id}/invites/{email}` | só o Dono |
| PATCH | `/api/playlists/{id}` | Dono (nome/visibilidade) |

Uma Playlist inacessível responde `404`; uma ação de Dono feita por outra pessoa responde `403`.
