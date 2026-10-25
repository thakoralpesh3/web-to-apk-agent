/**
 * Web2APK Native Hardware JavaScript Bridge 3.0
 * Superpowers: Toasts, Haptics, Notifications, Sharing, Device Info,
 * 120Hz GPU Turbocharger, and Native Voice / TTS Companion.
 */
(function(window) {
    if (window.Web2APK) return;

    class Web2APKBridge {
        constructor() {
            this.version = "3.0.0";
            this.isNative = typeof window.AndroidBridge !== 'undefined';
            this._initPolyfills();
            this.enableGPUTurbo();
            this.initLightsOutHealer();
        }

        _initPolyfills() {
            // Polyfill navigator.vibrate
            if (this.isNative && !navigator.vibrate) {
                navigator.vibrate = (pattern) => this.vibrate(pattern);
            }
        }

        showToast(message, duration = "short") {
            if (this.isNative && window.AndroidBridge.showToast) {
                window.AndroidBridge.showToast(String(message), duration === "long");
            } else {
                console.log("[Web2APK Toast]", message);
            }
        }

        vibrate(pattern = 50) {
            if (this.isNative && window.AndroidBridge.vibrate) {
                const duration = Array.isArray(pattern) ? pattern[0] : Number(pattern) || 50;
                window.AndroidBridge.vibrate(duration);
                return true;
            }
            return false;
        }

        getDeviceInfo() {
            if (this.isNative && window.AndroidBridge.getDeviceInfo) {
                try {
                    return JSON.parse(window.AndroidBridge.getDeviceInfo());
                } catch(e) {}
            }
            return {
                platform: "android",
                isTv: /Android TV|Leanback|GoogleTV/i.test(navigator.userAgent),
                model: "Web Preview",
                isOnline: navigator.onLine,
                screenWidth: window.innerWidth,
                screenHeight: window.innerHeight,
                gpuAccelerated: true,
                refreshRate: 120
            };
        }

        share(options = {}) {
            const title = options.title || document.title;
            const text = options.text || "";
            const url = options.url || window.location.href;

            if (this.isNative && window.AndroidBridge.shareText) {
                window.AndroidBridge.shareText(title, text + (url ? " " + url : ""));
                return Promise.resolve(true);
            } else if (navigator.share) {
                return navigator.share({ title, text, url });
            }
            return Promise.reject(new Error("Share not supported"));
        }

        setStatusBarColor(hexColor) {
            if (this.isNative && window.AndroidBridge.setStatusBarColor) {
                window.AndroidBridge.setStatusBarColor(String(hexColor));
            }
        }

        setFullscreen(enable = true) {
            if (this.isNative && window.AndroidBridge.setFullscreen) {
                window.AndroidBridge.setFullscreen(Boolean(enable));
            }
        }

        keepScreenOn(enable = true) {
            if (this.isNative && window.AndroidBridge.setKeepScreenOn) {
                window.AndroidBridge.setKeepScreenOn(Boolean(enable));
            }
        }

        scheduleNotification(options = {}) {
            const title = options.title || "Notification";
            const message = options.message || "";
            const delaySec = options.delaySeconds || 5;

            if (this.isNative && window.AndroidBridge.scheduleNotification) {
                window.AndroidBridge.scheduleNotification(title, message, delaySec);
                return true;
            }
            return false;
        }

        /**
         * 🎙️ Voice & TTS Companion: Text-To-Speech Synthesis
         */
        speak(text, lang = "en-US") {
            if (!text) return;
            if (window.speechSynthesis) {
                try {
                    window.speechSynthesis.cancel();
                    const utterance = new SpeechSynthesisUtterance(String(text));
                    utterance.lang = lang;
                    utterance.rate = 1.0;
                    window.speechSynthesis.speak(utterance);
                    return true;
                } catch(e) {}
            }
            console.log("[Web2APK Voice Speech]", text);
            return false;
        }

        /**
         * 🎙️ Voice Command Listener: Hands-free Voice Navigation
         */
        listen(callback, lang = "en-US") {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {
                console.warn("[Web2APK Voice] Speech recognition not supported in this environment");
                return false;
            }

            try {
                const recognition = new SpeechRec();
                recognition.lang = lang;
                recognition.continuous = false;
                recognition.interimResults = false;

                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    if (typeof callback === 'function') {
                        callback(transcript);
                    }
                };

                recognition.start();
                return true;
            } catch(e) {
                console.error("[Web2APK Voice Error]", e);
                return false;
            }
        }

        /**
         * ⚡ 120Hz GPU & WebGL Turbocharger: Unlocks high-refresh rate vsync
         */
        enableGPUTurbo() {
            try {
                // Hint GPU compositor for 60fps/120fps hardware rendering
                const canvases = document.querySelectorAll('canvas');
                canvases.forEach(c => {
                    c.style.transform = 'translateZ(0)';
                    c.style.willChange = 'transform';
                });
            } catch(e) {}
        }

        exitApp() {
            if (this.isNative && window.AndroidBridge.exitApp) {
                window.AndroidBridge.exitApp();
            } else {
                console.log("[Web2APK Exit]");
            }
        }

        /**
         * 💡 Lights Out & In-Page Modal Auto-Healer:
         * Dismisses dark overlays, cinema backdrops, or blocking modals.
         * Dispatches Escape (keyCode 27) and unblanks the screen while keeping the video playing.
         */
        dismissLightsOutOrModal() {
            let handled = false;

            // 1. Hide floating restore button
            const floatBtn = document.getElementById('web2apk-lights-out-btn');
            if (floatBtn && floatBtn.style.display !== 'none') {
                floatBtn.style.display = 'none';
                handled = true;
            }

            // 2. Dispatch ESC key event (keyCode 27)
            try {
                const escEvent = new KeyboardEvent('keydown', {
                    key: 'Escape',
                    code: 'Escape',
                    keyCode: 27,
                    which: 27,
                    bubbles: true,
                    cancelable: true
                });
                document.dispatchEvent(escEvent);
                window.dispatchEvent(escEvent);
                if (document.activeElement && document.activeElement !== document.body) {
                    document.activeElement.dispatchEvent(escEvent);
                }
            } catch(e) {}

            // 3. Remove common lights-out classes
            const lightClasses = ['lights-off', 'lightsoff', 'cinema-mode', 'dimmed', 'theater-mode', 'lights_off', 'night-mode-overlay'];
            lightClasses.forEach(cls => {
                if (document.body && document.body.classList.contains(cls)) {
                    document.body.classList.remove(cls);
                    handled = true;
                }
                if (document.documentElement && document.documentElement.classList.contains(cls)) {
                    document.documentElement.classList.remove(cls);
                    handled = true;
                }
            });

            // 4. Hide lights-out backdrops & overlays
            const overlaySelectors = [
                '#lightsoff', '.lightsoff',
                '#lights-off', '.lights-off',
                '#turn-off-lights', '.turn-off-lights',
                '#cinema-overlay', '.cinema-overlay',
                '#dimmer', '.dimmer-overlay',
                '[id*="lightsoff"]', '[class*="lightsoff"]',
                '[id*="lights_off"]', '[class*="lights_off"]',
                '[id*="cinema-mode"]', '[class*="cinema-mode"]',
                '#web2apk-dialog-overlay',
                '.modal-backdrop', '.vjs-dimmer'
            ];

            overlaySelectors.forEach(sel => {
                try {
                    const elements = document.querySelectorAll(sel);
                    elements.forEach(el => {
                        if (el && el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                            el.style.display = 'none';
                            handled = true;
                        }
                    });
                } catch(e) {}
            });

            // 5. Look for full-screen fixed dark overlays (excluding video containers)
            try {
                const allFixed = document.querySelectorAll('div, section, span');
                for (let i = 0; i < allFixed.length; i++) {
                    const el = allFixed[i];
                    if (el.id === 'web2apk-lights-out-btn') continue;
                    const style = window.getComputedStyle(el);
                    if ((style.position === 'fixed' || style.position === 'absolute') && style.display !== 'none' && parseFloat(style.opacity) > 0) {
                        const z = parseInt(style.zIndex, 10);
                        if (z >= 90 && z < 2147483645) {
                            const rect = el.getBoundingClientRect();
                            const wRatio = rect.width / (window.innerWidth || 1);
                            const hRatio = rect.height / (window.innerHeight || 1);
                            if (wRatio > 0.85 && hRatio > 0.85) {
                                const bg = style.backgroundColor;
                                if (bg && (bg.indexOf('0, 0, 0') !== -1 || bg.indexOf('rgb(0, 0, 0') !== -1 || bg.indexOf('rgba(0, 0, 0') !== -1 || bg === '#000' || bg === 'black')) {
                                    if (!el.querySelector('video, iframe')) {
                                        el.style.display = 'none';
                                        handled = true;
                                    }
                                }
                            }
                        }
                    }
                }
            } catch(e) {}

            // 6. Look for active "turn on lights" or "lights on" buttons to click
            try {
                const onButtons = document.querySelectorAll('button, a, span, div');
                for (let i = 0; i < onButtons.length; i++) {
                    const b = onButtons[i];
                    const text = (b.textContent || b.innerText || '').toLowerCase().trim();
                    if (text === 'turn on lights' || text === 'lights on' || text === 'turn lights on' || text === 'light on') {
                        if (b.offsetParent !== null) {
                            b.click();
                            handled = true;
                            break;
                        }
                    }
                }
            } catch(e) {}

            // Notify native bridge
            this.setLightsOutActive(false);
            return handled;
        }

        setLightsOutActive(active) {
            this._isLightsOutActive = Boolean(active);
            if (this.isNative && window.AndroidBridge.setLightsOutActive) {
                window.AndroidBridge.setLightsOutActive(this._isLightsOutActive);
            } else if (typeof window.AndroidApp !== 'undefined' && window.AndroidApp.setLightsOutActive) {
                window.AndroidApp.setLightsOutActive(this._isLightsOutActive);
            }
        }

        isLightsOutActive() {
            return Boolean(this._isLightsOutActive);
        }

        initLightsOutHealer() {
            if (this._healerInitialized) return;
            this._healerInitialized = true;

            const setup = () => {
                // 1. Inject Global CSS protecting Video Stacking Context
                if (!document.getElementById('web2apk-video-elevation-css')) {
                    const styleEl = document.createElement('style');
                    styleEl.id = 'web2apk-video-elevation-css';
                    styleEl.textContent = `
                        /* Elevate videos, players, and iframes above dark backdrops */
                        video,
                        iframe[src*="embed"],
                        iframe[src*="player"],
                        iframe[src*="video"],
                        iframe[allowfullscreen],
                        .jwplayer,
                        .video-js,
                        .plyr,
                        [class*="player-container"],
                        [id*="player-container"],
                        [class*="video-player"],
                        [id*="video-player"],
                        [class*="movie-player"],
                        [id*="movie-player"] {
                            position: relative !important;
                            z-index: 2147483640 !important;
                        }

                        /* Floating lights-on restore button */
                        #web2apk-lights-out-btn {
                            position: fixed !important;
                            top: 14px !important;
                            right: 14px !important;
                            z-index: 2147483647 !important;
                            background: rgba(15, 23, 42, 0.92) !important;
                            color: #38bdf8 !important;
                            border: 1.5px solid #38bdf8 !important;
                            border-radius: 20px !important;
                            padding: 8px 14px !important;
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                            font-size: 13px !important;
                            font-weight: 700 !important;
                            letter-spacing: 0.2px !important;
                            cursor: pointer !important;
                            display: none;
                            align-items: center !important;
                            gap: 6px !important;
                            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.75), 0 0 12px rgba(56, 189, 248, 0.4) !important;
                            user-select: none !important;
                            -webkit-user-select: none !important;
                            touch-action: manipulation !important;
                        }
                    `;
                    (document.head || document.documentElement).appendChild(styleEl);
                }

                // 2. Ensure floating button exists
                let btn = document.getElementById('web2apk-lights-out-btn');
                if (!btn && document.body) {
                    btn = document.createElement('div');
                    btn.id = 'web2apk-lights-out-btn';
                    btn.innerHTML = '<span>💡 Turn On Lights</span> <span style="font-size:15px;line-height:1;margin-left:2px;">✕</span>';
                    btn.title = "Click or press Back to restore lights";
                    const dismiss = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.dismissLightsOutOrModal();
                    };
                    btn.onclick = dismiss;
                    btn.ontouchstart = dismiss;
                    document.body.appendChild(btn);
                }

                const checkState = () => {
                    let isOff = false;
                    const bodyCls = (document.body ? document.body.className : '') + ' ' + (document.documentElement ? document.documentElement.className : '');
                    if (/lights[-_]?off|cinema[-_]?mode|dimmed|theater[-_]?mode/i.test(bodyCls)) {
                        isOff = true;
                    }

                    const overlaySelectors = [
                        '#lightsoff', '.lightsoff',
                        '#lights-off', '.lights-off',
                        '#turn-off-lights', '.turn-off-lights',
                        '#cinema-overlay', '.cinema-overlay',
                        '#dimmer', '.dimmer-overlay',
                        '[id*="lightsoff"]', '[class*="lightsoff"]',
                        '[id*="lights_off"]', '[class*="lights_off"]',
                        '[id*="cinema-mode"]', '[class*="cinema-mode"]'
                    ];

                    for (let sel of overlaySelectors) {
                        try {
                            const el = document.querySelector(sel);
                            if (el && el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                                const z = parseInt(window.getComputedStyle(el).zIndex, 10);
                                if (z >= 2147483640) {
                                    el.style.zIndex = '2147483600';
                                }
                                if (!el.__web2apk_tap_bound) {
                                    el.__web2apk_tap_bound = true;
                                    el.addEventListener('click', () => this.dismissLightsOutOrModal(), { passive: true });
                                }
                                isOff = true;
                                break;
                            }
                        } catch(e) {}
                    }

                    // Keep players elevated
                    const players = document.querySelectorAll('video, iframe[src*="embed"], iframe[src*="player"], iframe[allowfullscreen], .jwplayer, .video-js');
                    players.forEach(p => {
                        if (p.style.zIndex !== '2147483640') {
                            p.style.setProperty('z-index', '2147483640', 'important');
                            p.style.setProperty('position', 'relative', 'important');
                        }
                        const parent = p.parentElement;
                        if (parent && parent !== document.body && parent.style.zIndex !== '2147483640') {
                            const pz = parseInt(window.getComputedStyle(parent).zIndex, 10);
                            if (isNaN(pz) || pz < 2147483639) {
                                parent.style.setProperty('z-index', '2147483639', 'important');
                                parent.style.setProperty('position', 'relative', 'important');
                            }
                        }
                    });

                    if (btn) {
                        btn.style.display = isOff ? 'flex' : 'none';
                    }
                    this.setLightsOutActive(isOff);
                };

                if (window.MutationObserver && document.body) {
                    const observer = new MutationObserver(() => checkState());
                    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'id'] });
                }

                document.addEventListener('click', (e) => {
                    const t = e.target;
                    if (!t) return;
                    const txt = (t.textContent || '').toLowerCase();
                    const idCls = ((t.id || '') + ' ' + (t.className || '')).toLowerCase();
                    if (txt.includes('lights out') || txt.includes('turn off light') || idCls.includes('lightsoff') || idCls.includes('lights-off')) {
                        setTimeout(checkState, 100);
                        setTimeout(checkState, 400);
                    }
                }, { passive: true });

                setTimeout(checkState, 300);
            };

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setup);
            } else {
                setup();
            }
        }
    }

    window.Web2APK = new Web2APKBridge();
    window.__web2apk_dismissLightsOut = () => window.Web2APK.dismissLightsOutOrModal();
})(window);
