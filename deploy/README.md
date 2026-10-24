# Deploy no Oracle Cloud Always Free

O Musicat roda como um app Python (FastAPI) com SQLite e arquivos locais. No Oracle
Cloud ele fica numa VM com Docker: o app guarda tudo num volume persistente e o
Caddy termina HTTPS e faz proxy para ele.

Assumimos uma VM **Ubuntu 22.04/24.04** (Ampere ARM ou AMD). Os containers usam
imagens multi-arquitetura, então funciona nos dois.

## 1. VM e rede

1. Crie uma instância **Always Free** (Ampere A1 é a melhor opção; AMD micro serve).
2. Anote o **IP público**.
3. Na VCN → Security List (ou NSG), adicione ingress:
   - `0.0.0.0/0` TCP `80`
   - `0.0.0.0/0` TCP `443`
   - opcional: `0.0.0.0/0` UDP `443` (HTTP/3)
4. No firewall da VM:
   - Ubuntu (iptables do Oracle):
     ```bash
     sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
     sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
     sudo apt-get update && sudo apt-get install -y iptables-persistent
     sudo netfilter-persistent save
     ```
   - Oracle Linux (firewalld):
     ```bash
     sudo firewall-cmd --permanent --add-service=http
     sudo firewall-cmd --permanent --add-service=https
     sudo firewall-cmd --reload
     ```
5. Crie um DNS **A** `musicat.seudominio.com` → IP público da VM.
   - Se usar Cloudflare, deixe **DNS only** (nuvem cinza). Com proxy ligado, o
     limite de upload de ~100 MB do Cloudflare pode bloquear áudios grandes.

## 2. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

## 3. Projeto e configuração

```bash
git clone https://github.com/AmaranthD/musicat.git
cd musicat
cp deploy/.env.example .env
chmod 600 .env
nano .env
```

No `.env`, ajuste:

```env
MUSICAT_DOMAIN=musicat.seudominio.com
MUSICAT_SUPABASE_URL=https://SEU-PROJETO.supabase.co
MUSICAT_SUPABASE_KEY=sb_publishable_...
MUSICAT_CLAIM_LEGACY=0
```

Suba:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f musicat
```

Teste:

```bash
curl https://musicat.seudominio.com/healthz
# {"status":"ok"}
```

## 4. Supabase

Em **Authentication → URL Configuration**:

- **Site URL**: `https://musicat.seudominio.com`
- **Redirect URLs**: `https://musicat.seudominio.com/**`

Assim o link de confirmação de cadastro e a recuperação de senha voltam para o
domínio certo. O SMTP (Brevo) continua configurado no painel do Supabase.

## 5. Migrar a biblioteca local (opcional)

Se você já tem músicas no seu computador, copie `data/` para o volume **antes**
do primeiro login:

```bash
# pare a stack antes
docker compose stop musicat

docker run --rm \
  -v musicat_musicat_data:/data \
  -v "$PWD/data":/src \
  alpine sh -c 'cp -a /src/. /data/'

# para o primeiro login assumir os dados antigos:
# mude MUSICAT_CLAIM_LEGACY=1 no .env
docker compose up -d
```

O primeiro usuário a entrar assume as Faixas/Playlists antigas (claim). Depois
disso, volte para `MUSICAT_CLAIM_LEGACY=0`.

## 6. Backup

O volume `musicat_musicat_data` contém o SQLite e os arquivos. Backup:

```bash
docker run --rm \
  -v musicat_musicat_data:/data \
  -v "$PWD":/backup \
  alpine tar czf "/backup/musicat-$(date +%F).tar.gz" -C /data .
```

Guarde o `.tar.gz` fora da VM. Para restaurar, pare a stack, extraia no volume e
suba de novo.

## 7. Atualizar

```bash
git pull
docker compose up -d --build
```

O volume de dados não é afetado por rebuild.

## Cuidados

- **Nunca** rode `docker compose down -v`: isso apaga o volume e as músicas.
- Só as portas 80/443 ficam públicas; a porta 8000 do app fica interna na rede do
  Compose.
- O `.env` não vai para o Git. Não commite SMTP, service role nem tokens.
- O cookie de mídia já detecta `X-Forwarded-Proto: https` do Caddy.
- Em VM de 1 GB (AMD micro), considere 2 GB de swap e monitore `df -h`/`free -h`.
- Streaming usa a banda de upload da VM. O plano Always Free tem limite de tráfego
  de saída; acompanhe o consumo.
