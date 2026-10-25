# ☁️ How to Run Web2APK AI Studio 24/7 Online (Even When Laptop is OFF)

When you turn off your local laptop, local software stops running. To access **Web2APK AI Studio** 24/7 from your phone, tablet, or another computer from anywhere in the world, deploy it to a free cloud hosting provider.

---

## 🌟 Option 1: Render.com (100% Free 24/7 Web Hosting — Recommended)

Render provides free 24/7 web service hosting with custom domains and SSL.

1. Create a free account at [https://render.com](https://render.com).
2. Click **"New +"** $\to$ **"Web Service"**.
3. Connect your GitHub repository containing this `web-to-apk-agent` folder.
4. Render will automatically detect the included [`Dockerfile`](Dockerfile) and [`render.yaml`](render.yaml).
5. In **Environment Variables**, add:
   - `GEMINI_API_KEY`: `YOUR_GEMINI_API_KEY_HERE`
6. Click **"Create Web Service"**.
7. In ~2 minutes, your Web2APK AI Studio will be live at a public HTTPS URL (e.g. `https://web2apk-ai-studio.onrender.com`), accessible 24/7 from all devices even when your laptop is turned off!

---

## 🤗 Option 2: Hugging Face Spaces (100% Free 24/7 Docker Cloud)

1. Create a free account at [https://huggingface.co](https://huggingface.co).
2. Go to **Spaces** $\to$ **"Create new Space"** ([https://huggingface.co/new-space](https://huggingface.co/new-space)).
3. Name your space (e.g., `web2apk-studio`).
4. Select Space SDK: **Docker** (Blank).
5. Push this project code to your Hugging Face Space repository.
6. Your cloud studio is live 24/7 with zero maintenance!

---

## 🚂 Option 3: Railway.app / Fly.io

- **Railway**: Click "New Project" $\to$ "Deploy from GitHub repo" $\to$ Done!
- **Fly.io**: Run `fly launch` in this directory (uses pre-configured [`fly.toml`](fly.toml)).

---

## 🐳 Option 4: Local / VPS Background Docker Service

If you have a cloud VPS or home server that stays on:
```bash
cd /home/alpesh/web-to-apk-agent
docker compose up -d --build
```
