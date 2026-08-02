# Alex — AI Life Navigator

An AI life coach for young adults aged 16-25. Helps users build independence through structured coaching journeys.

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

## Deploy

This is a Flask app. Deploy to any platform that supports Python:

- **Render**: Connect GitHub repo → auto-deploy
- **Railway**: `railway up`
- **Any VPS**: `python server.py` behind nginx

Set `GOOGLE_API_KEY` as an environment variable on your hosting platform.
