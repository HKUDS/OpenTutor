# Troubleshooting

Quick solutions for common issues.

## Startup Issues

| Problem | Solution |
|:--------|:---------|
| Backend fails to start | Check Python ≥ 3.10, verify `.env` config |
| `npm: command not found` | Install Node.js: `conda install -c conda-forge nodejs` |
| Port already in use | Kill process: `lsof -i :8001` → `kill -9 <PID>` |

## Connection Issues

| Problem | Solution |
|:--------|:---------|
| Frontend can't reach backend | Verify backend at http://localhost:8001/docs |
| WebSocket fails | Check firewall, confirm `ws://localhost:8001/api/v1/...` format |
| Remote access fails | Set `NEXT_PUBLIC_API_BASE=http://your-ip:8001` in `.env` |

## Docker Issues

| Problem | Solution |
|:--------|:---------|
| Cloud frontend won't connect | Set `NEXT_PUBLIC_API_BASE_EXTERNAL=https://your-server:8001` |
| Wrong architecture | Check with `uname -m`: use `:latest` (AMD64) or `:latest-arm64` (ARM) |

## Knowledge Base

| Problem | Solution |
|:--------|:---------|
| Processing stuck | Check terminal logs, verify API keys |
| `uvloop.Loop` error | Run: `./scripts/extract_numbered_items.sh <kb_name>` |

## Kill Background Processes

```bash
# macOS/Linux
lsof -i :8001 && kill -9 <PID>

# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

---

📖 **Full FAQ**: [GitHub README](https://github.com/HKUDS/DeepTutor#-faq)
