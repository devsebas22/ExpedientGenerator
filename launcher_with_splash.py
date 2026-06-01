"""
Expediente Digital — Launcher con Splash Screen
Entry point que muestra una pantalla de carga inmediata mientras
launcher_main.py hace su trabajo (verificar licencia, actualizar, lanzar app).

Solo stdlib + tkinter.
"""

import sys
import threading

# ── Mutex check vía launcher_main (module-level code) ─────────────────────────
# Si ya hay otra instancia corriendo, launcher_main llama sys.exit(0),
# lo que lanza SystemExit aquí antes de mostrar nada — comportamiento correcto.
try:
    import launcher_main as _lm
except SystemExit as _e:
    sys.exit(_e.code)

# ── Splash screen ──────────────────────────────────────────────────────────────
try:
    import tkinter as tk
    _HAS_TK = True
except ImportError:
    _HAS_TK = False


class SplashScreen:
    W, H = 400, 200

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#ffffff")
        self.root.resizable(False, False)
        # Posicionar fuera de pantalla primero para evitar flash
        self.root.geometry(f"{self.W}x{self.H}+10000+10000")
        self.root.update_idletasks()
        # Centrar
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - self.W) // 2
        y  = (sh - self.H) // 2
        self.root.geometry(f"{self.W}x{self.H}+{x}+{y}")
        self.root.attributes("-topmost", True)

        # ── Cabecera: punto verde + título ────────────────────────────────────
        header = tk.Frame(self.root, bg="#ffffff")
        header.pack(pady=(55, 0))

        dot = tk.Canvas(header, width=14, height=14, bg="#ffffff", highlightthickness=0)
        dot.create_oval(1, 1, 13, 13, fill="#34c759", outline="")
        dot.pack(side="left", padx=(0, 8))

        tk.Label(
            header,
            text="Expediente Digital",
            font=("Segoe UI", 16, "bold"),
            fg="#1d1d1f",
            bg="#ffffff",
        ).pack(side="left")

        # ── Texto de estado ───────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Iniciando...")
        tk.Label(
            self.root,
            textvariable=self._status_var,
            font=("Segoe UI", 11),
            fg="#6e6e73",
            bg="#ffffff",
        ).pack(pady=(18, 0))

        self.root.update_idletasks()

    def set_text(self, text: str) -> None:
        try:
            self._status_var.set(text)
            self.root.update_idletasks()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    done_event = threading.Event()

    def run_launcher():
        try:
            _lm.main()
        except SystemExit:
            pass
        except Exception:
            pass
        finally:
            done_event.set()

    if _HAS_TK:
        splash = SplashScreen()
        t = threading.Thread(target=run_launcher, daemon=True)
        t.start()

        # Cambiar texto tras breve pausa para indicar verificación de licencia
        def show_verifying():
            if not done_event.is_set():
                splash.set_text("Verificando licencia...")

        def check_done():
            if done_event.is_set():
                splash.set_text("Listo")
                splash.root.after(400, splash.root.destroy)
            else:
                splash.root.after(80, check_done)

        splash.root.after(350, show_verifying)
        splash.root.after(80, check_done)
        splash.root.mainloop()
        t.join(timeout=2)
    else:
        run_launcher()


if __name__ == "__main__":
    main()
