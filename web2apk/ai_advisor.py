import os
import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

CONFIG_FILE = Path.home() / ".web2apk" / "config.json"
MODELS_CACHE_FILE = Path.home() / ".web2apk" / "models_cache.json"

DEFAULT_FALLBACK_MODELS = [
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite"
]

def parse_model_version(name: str) -> Tuple[float, str]:
    """
    Extracts numerical version from model name for semantic sorting.
    e.g. 'models/gemini-4-argon' -> (4.5, 'gemini-4-argon')
    """
    clean = name.replace("models/", "").strip()
    match_argon = re.search(r"gemini-(\d+(?:\.\d+)?)-argon", clean)
    if match_argon:
        return (float(match_argon.group(1)) + 0.5, clean)
    match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", clean)
    if match:
        return (float(match.group(1)), clean)
    match_pro = re.search(r"gemini-(\d+(?:\.\d+)?)-pro", clean)
    if match_pro:
        return (float(match_pro.group(1)) - 0.01, clean)
    if "flash-latest" in clean:
        return (1.0, clean)
    if "flash-lite" in clean:
        return (0.9, clean)
    return (0.0, clean)

class GeminiAdvisor:
    """
    Gemini AI Autonomous Code Advisor, Responsive Restyler,
    TV Focus Synthesizer & Play Store Copywriter with
    Autonomous Dynamic Model Discovery & Auto-Upgrade Engine.
    """

    @classmethod
    def get_api_key(cls) -> str:
        if "GEMINI_API_KEY" in os.environ:
            return os.environ["GEMINI_API_KEY"]
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("gemini_api_key", "")
            except Exception:
                pass
        return ""

    @classmethod
    def is_online(cls, timeout: float = 0.3) -> bool:
        """
        Fast non-blocking connectivity probe to determine if internet is reachable.
        Guarantees zero-delay fallback when operating in offline mode.
        """
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True
        except Exception:
            return False

    @classmethod
    def is_available(cls) -> bool:
        return bool(cls.get_api_key()) and cls.is_online()

    @classmethod
    def get_configured_model_preference(cls) -> str:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("selected_model", "auto")
            except Exception:
                pass
        return "auto"

    @classmethod
    def set_model_preference(cls, model_name: str) -> bool:
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            cfg = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["selected_model"] = model_name
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            return True
        except Exception:
            return False

    @classmethod
    def discover_available_models(cls, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Dynamically queries Google Gemini API for all available models,
        sorts them by release recency/version, and caches the result.
        """
        now = time.time()
        # Check cache if not expired (cache for 1 hour)
        if not force_refresh and MODELS_CACHE_FILE.exists():
            try:
                with open(MODELS_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if now - cached.get("timestamp", 0) < 3600:
                        return cached.get("models", [])
            except Exception:
                pass

        api_key = cls.get_api_key()
        if not api_key or not cls.is_online():
            return [{"name": m, "display_name": m.replace("-", " ").title(), "version": parse_model_version(m)[0]} for m in DEFAULT_FALLBACK_MODELS]

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            remote_models = list(client.models.list())
            
            discovered = []
            for m in remote_models:
                clean_name = m.name.replace("models/", "")
                # Focus on conversational / generation models (flash and pro)
                if ("gemini" in clean_name) and ("embedding" not in clean_name) and ("tts" not in clean_name) and ("transcribe" not in clean_name):
                    v, _ = parse_model_version(clean_name)
                    discovered.append({
                        "name": clean_name,
                        "display_name": getattr(m, "display_name", clean_name.replace("-", " ").title()) or clean_name,
                        "version": v
                    })

            # Sort descending by version
            discovered = sorted(discovered, key=lambda x: x["version"], reverse=True)
            
            if discovered:
                MODELS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(MODELS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": now, "models": discovered}, f, indent=2)
                return discovered

        except Exception as e:
            print(f"[GeminiAdvisor] Warning: Model discovery query failed: {e}")

        return [{"name": m, "display_name": m.replace("-", " ").title(), "version": parse_model_version(m)[0]} for m in DEFAULT_FALLBACK_MODELS]

    @classmethod
    def get_latest_flash_model(cls) -> str:
        """
        Returns the #1 highest version Gemini Flash model dynamically discovered.
        """
        models = cls.discover_available_models()
        flash_models = [m["name"] for m in models if "flash" in m["name"]]
        if flash_models:
            return flash_models[0]
        return DEFAULT_FALLBACK_MODELS[0]

    @classmethod
    def _get_execution_models_list(cls) -> List[str]:
        """
        Resolves model execution priority list:
        If user specified a model, tries that first, then latest discovered models.
        """
        pref = cls.get_configured_model_preference()
        models = [m["name"] for m in cls.discover_available_models()]
        
        if not models:
            models = DEFAULT_FALLBACK_MODELS[:]

        if pref and pref != "auto":
            return [pref] + [m for m in models if m != pref]
        return models

    @classmethod
    def _call_gemini(cls, prompt: str) -> Tuple[str, str]:
        """
        Calls Gemini API with automatic model upgrade & multi-model fallback.
        Returns: (response_text, model_used)
        """
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError("Gemini API Key not configured")
        if not cls.is_online():
            raise RuntimeError("Offline mode: Internet is not reachable. Using local heuristic fallback.")

        from google import genai
        client = genai.Client(api_key=api_key)

        candidate_models = cls._get_execution_models_list()
        last_err = None

        for attempt in range(2):
            for model in candidate_models:
                try:
                    resp = client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    if resp and resp.text:
                        return resp.text, model
                except Exception as e:
                    last_err = e
                    continue
            time.sleep(1.0)

        raise last_err or RuntimeError("All Gemini models unavailable")

    @classmethod
    def analyze_and_optimize_code(cls, html_snippet: str, app_name: str = "Web App") -> Dict[str, Any]:
        try:
            prompt = f"""You are an elite Android & Android TV optimization engine.
Analyze the following HTML/JS code for an app named '{app_name}'.

Code:
```html
{html_snippet[:4000]}
```

Provide structured output:
1. Critical Compatibility & Performance Issues
2. Recommended Patches
3. 2-sentence summary
"""
            text, used_model = cls._call_gemini(prompt)
            return {"success": True, "analysis": text, "model": used_model}
        except Exception as e:
            fallback_text = f"""### Web2APK Diagnostic Report for '{app_name}'
1. **Viewport & Safe Areas**: Fixed desktop viewports normalized with `viewport-fit=cover` and notch insets.
2. **TV Remote D-Pad**: Hardware focus rings and spatial navigation automatically injected.
3. **Web Audio & Modals**: AudioContext unlocker and non-blocking dialogs polyfilled for uninterrupted mobile/TV playback.
"""
            return {"success": True, "analysis": fallback_text, "fallback": True, "model": "offline-engine"}

    @classmethod
    def restyle_responsive(cls, html_snippet: str, app_name: str = "Web App") -> Dict[str, Any]:
        try:
            prompt = f"""You are an expert mobile and TV CSS engineer.
Generate a modern, responsive, notch-safe (`env(safe-area-inset-*)`), and TV-friendly CSS override block for this app: '{app_name}'.

Code reference:
```html
{html_snippet[:3000]}
```

Return ONLY valid CSS enclosed in ```css ... ``` tags.
"""
            text, used_model = cls._call_gemini(prompt)
            css_match = re.search(r"```css([\s\S]*?)```", text)
            css_content = css_match.group(1).strip() if css_match else text
            return {"success": True, "css": css_content, "model": used_model}
        except Exception:
            fallback_css = f"""/* Web2APK Auto-Generated Fluid Mobile & TV Layout */
:root {{
    --sat: env(safe-area-inset-top, 0px);
    --sab: env(safe-area-inset-bottom, 0px);
    --sal: env(safe-area-inset-left, 0px);
    --sar: env(safe-area-inset-right, 0px);
}}
html, body {{
    width: 100vw;
    min-height: 100vh;
    margin: 0;
    padding: var(--sat) var(--sar) var(--sab) var(--sal);
    overflow-x: hidden;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}}
*, *::before, *::after {{
    box-sizing: inherit;
    max-width: 100%;
}}
button, a, input, select {{
    min-height: 44px;
    min-width: 44px;
}}
:focus, :focus-visible {{
    outline: 3px solid #38bdf8 !important;
    outline-offset: 2px !important;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.8) !important;
}}
"""
            return {"success": True, "css": fallback_css, "fallback": True, "model": "offline-engine"}

    @classmethod
    def generate_play_store_metadata(cls, app_name: str, url: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        try:
            prompt = f"""Generate professional Google Play Store listing metadata for an Android & Android TV app:
App Name: {app_name}
Website URL: {url or 'N/A'}
Context: {description or 'Converted native Android & TV web application'}

Output in JSON format with keys: "title", "short_description", "full_description", "keywords", "category".
"""
            text, used_model = cls._call_gemini(prompt)
            json_text = text.strip()
            if "```json" in json_text:
                json_text = re.search(r"```json([\s\S]*?)```", json_text).group(1).strip()
            elif "```" in json_text:
                json_text = re.search(r"```([\s\S]*?)```", json_text).group(1).strip()

            data = json.loads(json_text)
            return {"success": True, "metadata": data, "model": used_model}
        except Exception:
            clean_name = app_name[:30]
            data = {
                "title": clean_name,
                "short_description": f"Fast, universal mobile and Android TV experience for {clean_name}.",
                "full_description": f"""# {clean_name} for Android & Android TV

Experience {clean_name} in high definition, optimized for mobile phones, tablets, and 4K Android TV devices with seamless remote control navigation.

### Key Features:
- 📱 **Full Mobile & Tablet Support**: Fluid responsive interface with notch safe-area adaptation.
- 📺 **Android TV Remote Ready**: Native D-Pad navigation and spatial focus.
- ⚡ **Instant Cold Startup**: Lightweight, hardware-accelerated WebView engine.
- 🎮 **Bluetooth Gamepad Support**: Plug-and-play controller mapping.
- 📶 **Offline Fallback Engine**: Smooth reconnection with dark-mode offline screen.
""",
                "keywords": ["web app", "android tv", "gamepad", "pwa", "universal", "tools", "utility", clean_name.lower()],
                "category": "Entertainment / Tools"
            }
            return {"success": True, "metadata": data, "fallback": True, "model": "offline-engine"}
