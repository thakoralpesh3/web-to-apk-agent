/**
 * Web2APK Gamepad & Bluetooth Controller Mapper
 * Maps standard Bluetooth controllers (Xbox, PS4/PS5, Android) to keyboard and touch events.
 */
(function(window) {
    class GamepadManager {
        constructor() {
            this.connectedGamepads = {};
            this.lastButtonState = {};
            this.active = false;
            this.init();
        }

        init() {
            window.addEventListener("gamepadconnected", (e) => {
                console.log("[Web2APK Gamepad] Connected:", e.gamepad.id);
                this.connectedGamepads[e.gamepad.index] = e.gamepad;
                if (!this.active) {
                    this.active = true;
                    this.poll();
                }
                if (window.Web2APK) {
                    window.Web2APK.showToast("🎮 Gamepad Connected: " + e.gamepad.id.split("(")[0]);
                }
            });

            window.addEventListener("gamepaddisconnected", (e) => {
                console.log("[Web2APK Gamepad] Disconnected:", e.gamepad.id);
                delete this.connectedGamepads[e.gamepad.index];
                if (Object.keys(this.connectedGamepads).length === 0) {
                    this.active = false;
                }
            });
        }

        poll() {
            if (!this.active) return;
            const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
            for (let i = 0; i < gamepads.length; i++) {
                const gp = gamepads[i];
                if (gp) {
                    this.processGamepad(gp);
                }
            }
            requestAnimationFrame(() => this.poll());
        }

        processGamepad(gp) {
            const keyMap = {
                12: "ArrowUp",
                13: "ArrowDown",
                14: "ArrowLeft",
                15: "ArrowRight",
                0: "Enter",   // A / Cross
                1: "Escape",  // B / Circle
                2: " ",       // X / Square
                3: "Shift"    // Y / Triangle
            };

            gp.buttons.forEach((btn, idx) => {
                const isPressed = btn.pressed || btn.value > 0.5;
                const wasPressed = this.lastButtonState[gp.index + "_" + idx] || false;

                if (isPressed && !wasPressed) {
                    const key = keyMap[idx];
                    if (key) {
                        this.dispatchKey(key, "keydown");
                    }
                } else if (!isPressed && wasPressed) {
                    const key = keyMap[idx];
                    if (key) {
                        this.dispatchKey(key, "keyup");
                    }
                }
                this.lastButtonState[gp.index + "_" + idx] = isPressed;
            });
        }

        dispatchKey(key, eventType) {
            const ev = new KeyboardEvent(eventType, {
                key: key,
                code: key,
                bubbles: true,
                cancelable: true
            });
            document.activeElement.dispatchEvent(ev);
            window.dispatchEvent(ev);
        }
    }

    window.Web2APKGamepad = new GamepadManager();
})(window);
