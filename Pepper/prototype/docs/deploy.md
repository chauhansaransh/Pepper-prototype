# Deploying the Pepper prototype

This app is a single Python process: static UI + JSON API + report generation. Host the **`prototype/`** directory (not the parent `Pepper/` folder unless you adjust paths).

## Before you push to GitHub

1. **Never commit secrets** — `.env` is gitignored; use host environment variables for `OPENROUTER_API_KEY`.
2. **Confirm `.gitignore`** includes `.venv/`, `.env`, `__pycache__/`, and local chart output if you do not want it in the repo.
3. **Add a repo README** at the root if the GitHub repo is the whole `Pepper` monorepo; point readers to `prototype/README.md`.

```bash
cd prototype
git init   # if not already in a repo
git add .
git commit -m "Add Pepper Atlas report prototype"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

## Environment variables (production)

| Variable | Required | Notes |
|----------|----------|--------|
| `OPENROUTER_API_KEY` | Yes | For LLM narratives; set only on the host, not in git |
| `OPENROUTER_MODEL` | No | Default `openai/gpt-oss-120b:free` |
| `HOST` | Yes on cloud | Must be `0.0.0.0` |
| `PORT` | Yes on cloud | Set by platform (e.g. Render uses `10000`) |
| `OPENROUTER_HTTP_REFERER` | Recommended | Your public URL (OpenRouter policy) |

## Option A — Render (simplest, free tier)

1. Push `prototype/` to GitHub (repo root = contents of `prototype`, **or** set **Root Directory** to `prototype` in Render).
2. [render.com](https://render.com) → **New** → **Web Service** → connect repo.
3. **Runtime:** Python 3  
   **Build:** `pip install -r requirements.txt`  
   **Start:** `python engine/api_server.py`
4. **Environment:** add `OPENROUTER_API_KEY`, `HOST=0.0.0.0`, and let Render inject `PORT` (often `10000`).
5. Set `OPENROUTER_HTTP_REFERER` to your Render URL after the first deploy.
6. Deploy → share `https://your-service.onrender.com`.

Or use the included `render.yaml` blueprint from the `prototype` folder.

**Note:** Free tier sleeps after inactivity; first load may take ~30s.

## Option B — Railway

1. New project from GitHub repo; root directory `prototype` if needed.
2. Start command: `python engine/api_server.py`
3. Add the same env vars; Railway sets `PORT` automatically — use `HOST=0.0.0.0`.

## Option C — Docker (Fly.io, Cloud Run, any VPS)

From `prototype/`:

```bash
docker build -t pepper-prototype .
docker run -p 8000:8000 \
  -e OPENROUTER_API_KEY="sk-or-..." \
  -e HOST=0.0.0.0 \
  -e PORT=8000 \
  pepper-prototype
```

## Option D — VPS (Ubuntu)

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO/prototype   # adjust if repo root is prototype
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export HOST=0.0.0.0 PORT=8000 OPENROUTER_API_KEY="..."
python engine/api_server.py
```

Put **nginx** or **Caddy** in front for HTTPS and use **systemd** to keep the process running.

## Security (public demos)

- Anyone with the URL can trigger report generation and **use your OpenRouter quota**.
- This prototype uses **mock data** only — safe for demos, not for real customer credentials.
- For a wider public launch later: add auth, rate limits, and separate API keys per environment.

## Verify after deploy

1. Open `/` — wizard loads.
2. Generate a weekly report for `acme-health`.
3. Check response JSON includes `usedLlm: true` and `llmProvider: "openrouter"` (or `llmError` if the key is missing).
4. Download PDF.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Site unreachable | Set `HOST=0.0.0.0`; use platform `PORT`, not hardcoded 8000 |
| LLM always falls back | `OPENROUTER_API_KEY` missing or invalid on host |
| Build fails on charts | Ensure `matplotlib` system libs (Dockerfile installs `libfreetype6`) |
| Logo missing | Add `peppercontent_logo.jpeg` at `prototype/peppercontent_logo.jpeg` or update UI path |
