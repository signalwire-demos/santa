# santa

A SignalWire AI Agent with automated GitHub → Dokku deployments.

## Features

- ✅ Auto-deploy on push to main/staging/develop
- ✅ Preview environments for pull requests
- ✅ Automatic SSL via Let's Encrypt
- ✅ Zero-downtime deployments
- ✅ Multi-environment support

## Setup

### 1. GitHub Secrets

Add these secrets to your repository (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `DOKKU_HOST` | Your Dokku server hostname |
| `DOKKU_SSH_PRIVATE_KEY` | SSH private key for deployments |
| `BASE_DOMAIN` | Base domain (e.g., `yourdomain.com`) |
| `SWML_BASIC_AUTH_USER` | Basic auth username |
| `SWML_BASIC_AUTH_PASSWORD` | Basic auth password |

### 2. GitHub Environments

Create these environments (Settings → Environments):
- `production` - Deploy from `main` branch
- `staging` - Deploy from `staging` branch
- `development` - Deploy from `develop` branch
- `preview` - Deploy from pull requests

### 3. Deploy

Just push to a branch:

```bash
git push origin main      # → santa.yourdomain.com
git push origin staging   # → santa-staging.yourdomain.com
git push origin develop   # → santa-dev.yourdomain.com
```

Or open a PR for a preview environment.

## Branch → Environment Mapping

| Branch | App Name | URL |
|--------|----------|-----|
| `main` | `santa` | `santa.yourdomain.com` |
| `staging` | `santa-staging` | `santa-staging.yourdomain.com` |
| `develop` | `santa-dev` | `santa-dev.yourdomain.com` |
| PR #42 | `santa-pr-42` | `santa-pr-42.yourdomain.com` |

## Manual Operations

```bash
# View logs
ssh dokku@server logs santa -t

# SSH into container
ssh dokku@server enter santa

# Restart
ssh dokku@server ps:restart santa

# Rollback
ssh dokku@server releases:rollback santa

# Scale
ssh dokku@server ps:scale santa web=2
```

## Local Development

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

Test with swaig-test:
```bash
swaig-test app.py --list-tools
```
