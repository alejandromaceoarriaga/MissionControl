# OpenClaw + n8n Stack

> Your personal AI operating system in a box. Run AI agents with workflow automation — self-hosted, fully customizable.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## What Is This?

A pre-configured Docker stack that combines:

- **[OpenClaw](https://github.com/openclaw/openclaw)** — Personal AI agent gateway (Claude-powered)
- **[n8n](https://n8n.io)** — Visual workflow automation (400+ integrations)

Together, they form a powerful AI automation platform where your agent can trigger workflows, call webhooks, process data, and interact with external services.

## Why This Stack?

| Capability | OpenClaw | n8n | Combined |
|------------|----------|-----|----------|
| AI reasoning | ✅ | ❌ | ✅ |
| Workflow automation | ❌ | ✅ | ✅ |
| External integrations | Limited | 400+ | ✅ |
| Visual workflow builder | ❌ | ✅ | ✅ |
| Natural language interface | ✅ | ❌ | ✅ |
| Self-hosted | ✅ | ✅ | ✅ |

**Example use cases:**
- AI agent that triages your email and sends Slack summaries
- Content pipeline: research → write → fact-check → publish
- Social media monitoring with AI-powered responses
- Automated reporting with natural language queries
- Multi-model AI validation (Claude + ChatGPT + Gemini)

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- An Anthropic API key (for Claude)
- Optional: OpenAI and/or Google AI keys for multi-model workflows

### 1. Clone and Configure

```bash
git clone https://github.com/caprihan/openclaw-n8n-stack.git
cd openclaw-n8n-stack

# Copy the environment template
cp .env.template .env

# Edit with your API keys
nano .env
```

### 2. Start the Stack

```bash
docker-compose up -d
```

### 3. Access the Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| n8n | http://localhost:5678 | admin / (your password) |
| OpenClaw | http://localhost:3456 | — |

### 4. Import Example Workflows

The `workflows/` directory contains ready-to-use n8n workflows:

1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import from File**
3. Import any workflow from the `workflows/` directory
4. Configure credentials and activate

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│                                                              │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │    OpenClaw     │◄───────►│      n8n        │            │
│  │   (AI Agent)    │ webhook │  (Workflows)    │            │
│  │   Port 3456     │         │   Port 5678     │            │
│  └────────┬────────┘         └────────┬────────┘            │
│           │                           │                      │
│           ▼                           ▼                      │
│    ┌──────────────┐           ┌──────────────┐              │
│    │  workspace/  │           │  workflows/  │              │
│    │  (your files)│           │ (n8n exports)│              │
│    └──────────────┘           └──────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │                               │
         ▼                               ▼
   Anthropic API                  External Services
   OpenAI API                     (Slack, Gmail, etc.)
   Google AI API
```

## Included Workflows

| Workflow | Description |
|----------|-------------|
| `ripr-chatgpt-validator.json` | Multi-LLM fact-checking (ChatGPT) |
| `ripr-gemini-validator.json` | Multi-LLM fact-checking (Gemini) |
| `email-triage.json` | AI-powered email summarization |
| `social-monitor.json` | Track mentions and trends |

## Configuration

### OpenClaw Config

Edit `config/openclaw.json` to customize:
- Default model and thinking level
- Skills and tools enabled
- Channel configurations

### n8n Credentials

Set up credentials in n8n UI:
1. Go to **Credentials** → **Add Credential**
2. Add your API keys for services you'll use
3. Reference them in your workflows

## Connecting OpenClaw to n8n

OpenClaw can call n8n webhooks directly. In your agent workspace:

```bash
# Example: Call a n8n workflow from OpenClaw
curl -X POST "http://n8n:5678/webhook/my-workflow" \
  -H "Content-Type: application/json" \
  -d '{"data": "from openclaw"}'
```

The `N8N_WEBHOOK_BASE` environment variable is pre-configured so OpenClaw knows where to find n8n.

## Updating

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

## Backup

```bash
# Backup volumes
docker run --rm -v openclaw-n8n-stack_openclaw-data:/data -v $(pwd):/backup alpine tar czf /backup/openclaw-backup.tar.gz -C /data .
docker run --rm -v openclaw-n8n-stack_n8n-data:/data -v $(pwd):/backup alpine tar czf /backup/n8n-backup.tar.gz -C /data .
```

## Troubleshooting

### n8n can't connect to OpenClaw
- Ensure both containers are on the same network
- Check `docker-compose logs openclaw` for errors
- Verify API keys are set correctly

### Webhooks not working externally
- Update `N8N_WEBHOOK_URL` in `.env` to your public URL
- Ensure port 5678 is accessible

### Out of disk space
- Check Docker volumes: `docker system df`
- Prune unused: `docker system prune -a`

## Security Notes

⚠️ **For production deployment:**

1. Use strong passwords for n8n
2. Put behind a reverse proxy with HTTPS
3. Don't expose ports directly to the internet
4. Keep API keys secure (never commit `.env`)
5. Review n8n's [security best practices](https://docs.n8n.io/hosting/security/)

## Contributing

PRs welcome! Especially:
- New workflow templates
- Documentation improvements
- Security hardening

## Credits

- [OpenClaw](https://github.com/openclaw/openclaw) — AI agent framework
- [n8n](https://n8n.io) — Workflow automation
- Built by [Gaurav Caprihan](https://linkedin.com/in/gauravcaprihan) / [Gripsy](https://gripsy.com.au)

## License

MIT — Use it, modify it, build on it.

---

**Get a grip on AI.** 🦎
