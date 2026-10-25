#!/usr/bin/env bash
# ==============================================================================
# Web2APK 24/7 Online Cloud Deployment Script
# Deploys Web2APK AI Studio to 24/7 Cloud Platforms (Render, Hugging Face, VPS)
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================================"
echo "☁️  Web2APK AI Studio: 24/7 Online Cloud Deployer"
echo "======================================================================"
echo "Run Web2APK online 24/7 so it is accessible even when your laptop is OFF!"
echo ""
echo "Choose your 24/7 Cloud Deployment target:"
echo "  1) 🌟 Render.com (100% Free 24/7 Web Service - Recommended)"
echo "  2) 🤗 Hugging Face Spaces (100% Free 24/7 Docker Container)"
echo "  3) 🚂 Railway.app / Fly.io (Fast 1-Click Cloud Hosting)"
echo "  4) 🐳 Local/VPS Docker Container (Runs 24/7 in background)"
echo "  5) 📖 View 24/7 Cloud Step-by-Step Guide"
echo "======================================================================"

read -p "Select an option [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Deploying to Render.com (Free 24/7 Cloud Service):"
        echo "1. Push this repository to GitHub or GitLab."
        echo "2. Go to https://dashboard.render.com -> 'New +' -> 'Web Service'."
        echo "3. Connect your repository."
        echo "4. Render will automatically detect 'Dockerfile' or 'render.yaml'."
        echo "5. Add Environment Variable: GEMINI_API_KEY = (your key)"
        echo "6. Click 'Create Web Service' -> You will get a permanent 24/7 URL!"
        echo "   Example: https://web2apk-ai-studio.onrender.com"
        ;;
    2)
        echo ""
        echo "🤗 Deploying to Hugging Face Spaces (Free 24/7 Hosting):"
        echo "1. Go to https://huggingface.co/new-space"
        echo "2. Space Name: web2apk-ai-studio"
        echo "3. Select Space SDK: 'Docker' (Blank template)"
        echo "4. Push this repository to the Hugging Face Space git remote."
        echo "5. Your 24/7 Web2APK Studio will immediately be live online!"
        ;;
    3)
        echo ""
        echo "🚂 Deploying to Railway / Fly.io:"
        echo "For Railway:"
        echo "  - Run: 'railway login' then 'railway up'"
        echo "For Fly.io:"
        echo "  - Run: 'fly launch' (fly.toml is already configured)"
        ;;
    4)
        echo ""
        echo "🐳 Building & Running 24/7 Docker Container..."
        if command -v docker >/dev/null 2>&1; then
            docker compose up -d --build
            echo "✓ Web2APK Container is now running 24/7 in background on http://localhost:8990"
        else
            echo "❌ Docker not installed on this system. Please install docker or choose Option 1."
        fi
        ;;
    5)
        cat "$DIR/README_CLOUD.md"
        ;;
    *)
        echo "Invalid selection."
        ;;
esac
