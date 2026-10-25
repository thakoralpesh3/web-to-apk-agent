import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

MEMORY_FILE = Path.home() / ".web2apk" / "memory.json"
INNOVATIONS_FILE = Path.home() / ".web2apk" / "innovations.json"

class EvolutionEngine:
    """
    Self-Learning & Evolutionary Growth Engine 3.0.
    Tracks project structures, masters framework patterns, records self-healing
    successes, evolves the agent's internal intelligence, and synthesizes
    groundbreaking autonomous innovations and surprises.
    """

    FRAMEWORK_SIGNATURES = {
        "Phaser 3 Game Engine": [r"phaser\.min\.js", r"phaser\.js", r"Phaser\.Game"],
        "Three.js / WebGL 3D": [r"three\.min\.js", r"three\.js", r"THREE\.Scene", r"three/build"],
        "Godot Engine HTML5": [r"godot\.js", r"engine\.js", r"\$Godot"],
        "Construct 3 / 2": [r"c3runtime\.js", r"c2runtime\.js"],
        "Unity WebGL": [r"UnityLoader\.js", r"unityInstance", r"Build/.*\.framework\.js"],
        "React SPA": [r"react\.production\.min\.js", r"react-dom", r"_react", r"__REACT_DEVTOOLS_GLOBAL_HOOK__"],
        "Vue.js App": [r"vue\.min\.js", r"vue\.runtime", r"__VUE__", r"v-app"],
        "Vite Modern Bundle": [r"@vite", r"/assets/index-.*\.js", r"vite/client"],
        "Next.js Static Export": [r"_next/static", r"__NEXT_DATA__"],
        "Svelte Framework": [r"svelte", r"__svelte"],
        "PixiJS 2D Engine": [r"pixi\.min\.js", r"PIXI\.Application"],
        "Tailwind CSS App": [r"tailwindcss", r"tailwind\.css"],
        "Vanilla HTML5 / Modern JS": []
    }

    @classmethod
    def identify_framework(cls, dir_path: Path) -> str:
        all_text = ""
        files = list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.js")) + list(dir_path.glob("package.json"))
        
        for f in files[:15]:
            try:
                all_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"
            except Exception:
                pass

        for framework, signatures in cls.FRAMEWORK_SIGNATURES.items():
            for sig in signatures:
                if re.search(sig, all_text):
                    return framework

        return "Vanilla HTML5 / Modern JS"

    @classmethod
    def load_memory(cls) -> Dict[str, Any]:
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        default_memory = {
            "version": "3.0.0",
            "xp": 150,
            "level": 1,
            "rank": "Apprentice AI Builder",
            "total_builds": 0,
            "successful_builds": 0,
            "total_repairs_applied": 0,
            "innovations_invented": 0,
            "frameworks_mastered": {},
            "learned_solutions": [
                "Auto-promotes nested build folders (dist, build, out) to root index.html",
                "Injects D-Pad Spatial Navigation polyfill for TV remote control",
                "Unlocks suspended Web Audio contexts on first user/remote interaction",
                "Replaces blocking window.alert/confirm dialogs with non-blocking modern UI",
                "Auto-detects Camera, Mic, and Geolocation APIs and adds Android permissions",
                "Journals build checkpoints to instantly auto-resume interrupted sessions on crash",
                "Injects 120Hz GPU Turbocharger & Hardware Vsync for buttery smooth 60/120 FPS games",
                "Polyfills Native TTS Voice Companion (window.Web2APK.speak) & Hands-Free Remote commands",
                "Synthesizes zero-dependency Service Workers & Manifests for 100% offline PWA execution"
            ],
            "build_history": []
        }
        cls.save_memory(default_memory)
        return default_memory

    @classmethod
    def save_memory(cls, data: Dict[str, Any]):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_innovations(cls) -> List[Dict[str, Any]]:
        if INNOVATIONS_FILE.exists():
            try:
                with open(INNOVATIONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    @classmethod
    def record_innovation(cls, innovation: Dict[str, Any]):
        innovations = cls.load_innovations()
        innovation["timestamp"] = int(time.time())
        innovations = [innovation] + innovations[:50]
        INNOVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INNOVATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(innovations, f, indent=2)

    @classmethod
    def calculate_rank(cls, xp: int) -> Tuple[int, str]:
        level = min(10, 1 + xp // 300)
        ranks = {
            1: "Apprentice AI Builder",
            2: "Junior Web2APK Engineer",
            3: "Adaptive Code Optimizer",
            4: "Android TV Specialist",
            5: "Multi-Platform Master",
            6: "Autonomous Self-Healer",
            7: "Advanced Systems Architect",
            8: "High-Performance Compiler AI",
            9: "Evolutionary Grandmaster",
            10: "Transcendent Universal Singularity"
        }
        return level, ranks.get(level, "Universal Agent")

    @classmethod
    def record_build(
        cls,
        app_name: str,
        framework: str,
        success: bool,
        repairs: List[str],
        permissions: List[str],
        apk_size_mb: float = 0.0
    ) -> Dict[str, Any]:
        mem = cls.load_memory()
        mem["total_builds"] += 1
        if success:
            mem["successful_builds"] += 1
            xp_gained = 50 + (len(repairs) * 25)
            mem["xp"] += xp_gained
        else:
            mem["xp"] += 10

        f_count = mem["frameworks_mastered"].get(framework, 0)
        mem["frameworks_mastered"][framework] = f_count + 1

        mem["total_repairs_applied"] += len(repairs)

        lvl, rnk = cls.calculate_rank(mem["xp"])
        mem["level"] = lvl
        mem["rank"] = rnk

        entry = {
            "timestamp": int(time.time()),
            "app_name": app_name,
            "framework": framework,
            "success": success,
            "repairs_count": len(repairs),
            "permissions": permissions,
            "apk_size_mb": apk_size_mb
        }
        mem["build_history"] = ([entry] + mem.get("build_history", []))[:30]

        cls.save_memory(mem)
        return {
            "level": mem["level"],
            "rank": mem["rank"],
            "xp": mem["xp"],
            "total_builds": mem["total_builds"],
            "repairs_total": mem["total_repairs_applied"],
            "innovations_total": len(cls.load_innovations())
        }

    @classmethod
    def generate_surprise_innovations(
        cls,
        app_name: str = "Web App",
        html_snippet: str = "",
        framework: str = "Vanilla HTML5 / Modern JS"
    ) -> Dict[str, Any]:
        """
        Synthesizes 3 visionary, tailored surprises and feature upgrade proposals for the app
        using Gemini 3.8 Flash (with bulletproof offline heuristic fallback).
        """
        from .ai_advisor import GeminiAdvisor

        prompt = f"""You are an elite, visionary Android & Web Innovations Architect.
Analyze the following app and invent 3 GROUNDBREAKING, SURPRISING, and HIGH-VALUE feature upgrades specifically tailored for it:

App Name: {app_name}
Framework: {framework}
Code snippet:
```html
{html_snippet[:2500]}
```

Return JSON array with exactly 3 innovation objects.
Each object must have:
- "title": (Punchy feature name with emoji e.g. "🎙️ AI Voice Command Companion")
- "category": ("Gaming & Performance" | "TV & Smart Screens" | "AI & Immersion" | "Security & Monetization")
- "tagline": (1-sentence visionary hook)
- "description": (Detailed explanation of why this will blow the user away)
- "action_type": ("gpu_turbo" | "voice_tts" | "pwa_offline" | "gamepad_map" | "dark_glass")
- "readiness": ("Ready to Apply Immediately")
"""
        try:
            if GeminiAdvisor.is_available():
                text, used_model = GeminiAdvisor._call_gemini(prompt)
                json_text = text.strip()
                if "```json" in json_text:
                    json_text = re.search(r"```json([\s\S]*?)```", json_text).group(1).strip()
                elif "```" in json_text:
                    json_text = re.search(r"```([\s\S]*?)```", json_text).group(1).strip()

                proposals = json.loads(json_text)
                if isinstance(proposals, list) and len(proposals) > 0:
                    cls.record_innovation({
                        "app_name": app_name,
                        "model": used_model,
                        "proposals": proposals
                    })
                    return {"success": True, "proposals": proposals, "model": used_model}
        except Exception as e:
            print(f"[EvolutionEngine] Warning in AI surprise generation: {e}")

        # Fallback Visionary Surprises
        fallback_proposals = [
            {
                "title": "⚡ 120Hz GPU Turbocharger & Vsync Uncap",
                "category": "Gaming & Performance",
                "tagline": "Unleashes high-refresh rate 120 FPS hardware acceleration on modern Android OLED displays.",
                "description": "Bypasses default 60Hz WebView throttling, forces hardware canvas composition layers, and optimizes requestAnimationFrame for ultra-fluid gameplay and animations.",
                "action_type": "gpu_turbo",
                "readiness": "Ready to Apply Immediately"
            },
            {
                "title": "🎙️ Hands-Free Voice Assistant & TTS Companion",
                "category": "AI & Immersion",
                "tagline": "Enables native speech synthesis and remote voice commands via window.Web2APK.speak().",
                "description": "Allows users to navigate through Android TV remotes and phones using speech recognition, while giving your web app the ability to speak out loud with zero latency.",
                "action_type": "voice_tts",
                "readiness": "Ready to Apply Immediately"
            },
            {
                "title": "📴 Autonomous Standalone PWA-to-Offline Synthesizer",
                "category": "Smart Utility",
                "tagline": "Synthesizes an intelligent Service Worker and Web Manifest for 100% offline playback.",
                "description": "Pre-caches all critical assets, scripts, audio samples, and CSS into persistent CacheStorage so your app launches in under 150ms even with Airplane Mode enabled.",
                "action_type": "pwa_offline",
                "readiness": "Ready to Apply Immediately"
            }
        ]

        cls.record_innovation({
            "app_name": app_name,
            "model": "offline-singularity-heuristics",
            "proposals": fallback_proposals
        })

        return {"success": True, "proposals": fallback_proposals, "model": "offline-singularity"}
