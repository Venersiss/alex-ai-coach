# Alex — AI Life Navigator

An AI life coach for young adults aged 16-25. Helps users build independence through structured coaching journeys.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Venersiss/alex-ai-coach)

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Gemini API key from https://aistudio.google.com
python server.py
```

Open **http://localhost:5000** in your browser.

## Journeys

- **Journey 1** — Emergency Independence ("I got kicked out")
- **Journey 2** — Aged Out of Foster Care

## Run Tests

```bash
python test_e2e.py
```

## Deploy to Render

1. Click the **Deploy to Render** button above
2. Sign in with GitHub
3. Set `GOOGLE_API_KEY` to your Gemini API key
4. Click **Apply** — Render deploys automatically

After deployment, you'll get a public URL like `alex-ai-coach.onrender.com`.

Every `git push` to `master` redeploys automatically.
