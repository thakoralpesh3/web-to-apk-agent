# Web2APK AI Agent: Universal Web to Android APK Converter & Cloud Studio

[![Web2APK CI](https://github.com/thakoralpesh3/web-to-apk-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/thakoralpesh3/web-to-apk-agent/actions/workflows/ci.yml)
[![24/7 Cloud Issue Bot](https://github.com/thakoralpesh3/web-to-apk-agent/actions/workflows/issue-build.yml/badge.svg)](https://github.com/thakoralpesh3/web-to-apk-agent/actions/workflows/issue-build.yml)

Autonomous AI Agent that converts live websites, HTML5 apps, PWAs, or web folders into production-ready Android Phone and Android TV APKs. Includes Native Google AAPT2 compilation, R8 Dex Bytecode generation, Self-Healing problem solver, and 24/7 Cloud operation.

---

## ⚡ 24/7 Cloud Execution (No Laptop Needed!)

### Option A: 24/7 GitHub Issue Bot
You can trigger APK builds from your phone or any browser without running code locally:
1. Go to **Issues** ➔ **New Issue**.
2. **Title**: `[Build] My Cool App`
3. **Body**: `https://mywebsite.com`
4. Click **Submit new issue**.
5. Within 2–3 minutes, GitHub Actions will compile, sign, and release the APK, replying with the download link directly in the issue!

### Option B: GitHub Actions UI
1. Go to the **Actions** tab ➔ **Run Web2APK Packaging Cycle**.
2. Click **Run workflow**, enter your URL, target device (`smartphone` or `tv`), and fullscreen mode.
3. Download the signed APK directly from **Releases** or **Artifacts**.

### Option C: 24/7 Web Studio Dashboard (Render.com)
Deploy your own 24/7 live web dashboard on Render's free tier with 1 click using the bundled `render.yaml`:
1. Log in to [Render.com](https://dashboard.render.com).
2. Click **New +** ➔ **Blueprint** and connect `thakoralpesh3/web-to-apk-agent`.
3. Your Web Studio will be live 24/7 on a public HTTPS URL.

---

## 🛠️ 1-Command Cloud & VPS Installer
```bash
curl -fsSL https://raw.githubusercontent.com/thakoralpesh3/web-to-apk-agent/main/install_and_run.sh | bash
```

---

## 🌟 Key Features
- **Smartphone & Android TV Dual Targets**: Native Leanback support, D-Pad navigation, and touch simulation.
- **Genuine Native Toolchain**: Uses AAPT2 + R8 compiler for 100% Google Play compliant APKs.
- **In-App Authenticated Downloads**: Supports SQLite, SQL, JSON, and CSV database exports without saving as HTML.
- **Wi-Fi QR Sideloading**: Download and test immediately on physical Android devices.
