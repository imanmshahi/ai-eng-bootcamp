# Deploy API to Render

> **The live service is https://ai-eng-bootcamp-v4if.onrender.com — check that host only.**
>
> Two other hosts answer `200` on `/health` and are NOT this project:
> `ai-eng-bootcamp-api.onrender.com` (old, abandoned Week-1 build: only `/ask` and `/health`)
> and `ai-eng-bootcamp.onrender.com` (an unrelated app). Because both reply successfully, a
> check against either reads as a healthy check of a stale deployment rather than as a mistake.
> This document previously used the `-api` host as its example URL, which is how the mix-up
> propagated. See F11 in `evals/FINDINGS.md`.

What **deploy** means: your FastAPI app runs on Render's computers 24/7 at a public URL — here `https://ai-eng-bootcamp-v4if.onrender.com`. Anyone (you, cohort, curl) can call `/health`, `/ask`, `/estimate` without your laptop on.

**What stays local:** Streamlit UI (`./start.sh`) unless you later use Streamlit Cloud.

---

## What you get

| Before (local) | After (Render) |
|----------------|----------------|
| `http://127.0.0.1:8000/ask` | `https://ai-eng-bootcamp-v4if.onrender.com/ask` |
| Laptop must be on | API runs in the cloud |
| `.env` on your machine | `OPENAI_API_KEY` in Render dashboard |

---

## Steps (one time, ~10 min)

### 1. Push is done

Repo: https://github.com/CTATX/ai-eng-bootcamp (includes `Dockerfile`, `render.yaml`)

### 2. Create Render account

https://render.com — sign up with GitHub.

### 3. New Blueprint / Web Service

**Option A — Blueprint (easiest):**

1. Render Dashboard → **New** → **Blueprint**
2. Connect **CTATX/ai-eng-bootcamp**
3. Render reads `render.yaml` and creates the service named in it. Confirm the name
   matches the EXISTING live service first — a mismatch creates a second service
   instead of updating the live one.

**Option B — Manual Web Service:**

1. **New** → **Web Service** → connect repo
2. **Runtime:** Docker
3. **Branch:** main
4. **Health check path:** `/health`

### 4. Set secret on Render

In the service → **Environment**:

| Key | Value |
|-----|--------|
| `OPENAI_API_KEY` | your `sk-proj-...` key |

Never commit this. Render injects it at runtime (same idea as local `.env`).

### 5. Deploy

Render builds the Docker image and starts uvicorn. When green:

```bash
curl https://ai-eng-bootcamp-v4if.onrender.com/health
curl -X POST https://ai-eng-bootcamp-v4if.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is an API?"}'
```

Interactive docs: `https://ai-eng-bootcamp-v4if.onrender.com/docs`

---

## Use local Streamlit against cloud API

```bash
export API_BASE=https://ai-eng-bootcamp-v4if.onrender.com
./start.sh
```

Or only Streamlit (no local uvicorn):

```bash
export API_BASE=https://ai-eng-bootcamp-v4if.onrender.com
streamlit run app.py
```

---

## badlabz link (static site)

On https://github.com/CTATX/badlabz or your domain, add a page:

```html
<a href="https://ai-eng-bootcamp-v4if.onrender.com/docs">Bootcamp API demo</a>
```

GitHub Pages hosts the **link**; Render hosts the **API**.

---

## Free tier note

Render free services **spin down after idle** (~50s cold start on first request). Fine for demos and cohort; upgrade if you need always-hot.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails | Check Render logs; confirm `Dockerfile` in repo |
| 503 on `/ask` | Set `OPENAI_API_KEY` in Render env |
| 401 on `/ask` | Wrong key or Cursor key — use OpenAI key |
| Slow first request | Free tier waking up — normal |
