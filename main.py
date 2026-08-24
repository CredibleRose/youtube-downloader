import os
import platform
import re
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from yt_dlp import YoutubeDL

QUALITIES = ["Лучшее", "1080p", "720p", "480p", "360p"]
QUALITY_HEIGHT = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
BROWSERS = ["Нет", "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi"]
BROWSER_KEYS = {
    "Chrome": "chrome",
    "Edge": "edge",
    "Firefox": "firefox",
    "Brave": "brave",
    "Opera": "opera",
    "Vivaldi": "vivaldi",
}

DEFAULT_OUTPUT_DIR = str(Path.home() / "Videos" / "YouTube Downloads")


def _bundled_tool_path(name):
    """Look for a tool (ffmpeg/deno) bundled next to a frozen PyInstaller build."""
    if not getattr(sys, "frozen", False):
        return None
    exe_name = f"{name}.exe" if platform.system() == "Windows" else name
    candidate = Path(sys.executable).resolve().parent / exe_name
    if candidate.exists():
        return str(candidate)
    return None


FFMPEG_PATH = _bundled_tool_path("ffmpeg") or shutil.which("ffmpeg")
DENO_PATH = _bundled_tool_path("deno") or shutil.which("deno")


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        root.title("YouTube Downloader")
        root.geometry("640x480")
        root.minsize(560, 420)

        self.download_thread = None
        self.cancel_requested = False

        self._build_ui()
        self._check_ffmpeg()

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill="x", **pad)
        ttk.Label(url_frame, text="Ссылка на видео / плейлист:").pack(anchor="w")
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        url_entry.pack(fill="x", pady=(2, 0))
        self._add_context_menu(url_entry)
        url_entry.focus_set()

        options_frame = ttk.LabelFrame(self.root, text="Параметры")
        options_frame.pack(fill="x", **pad)

        row1 = ttk.Frame(options_frame)
        row1.pack(fill="x", padx=8, pady=4)

        self.mode_var = tk.StringVar(value="video")
        ttk.Radiobutton(row1, text="Видео (mp4)", variable=self.mode_var,
                         value="video", command=self._on_mode_change).pack(side="left")
        ttk.Radiobutton(row1, text="Только аудио (mp3)", variable=self.mode_var,
                         value="audio", command=self._on_mode_change).pack(side="left", padx=(12, 0))

        ttk.Label(row1, text="Качество:").pack(side="left", padx=(20, 4))
        self.quality_var = tk.StringVar(value=QUALITIES[0])
        self.quality_combo = ttk.Combobox(row1, textvariable=self.quality_var,
                                           values=QUALITIES, state="readonly", width=10)
        self.quality_combo.pack(side="left")

        row2 = ttk.Frame(options_frame)
        row2.pack(fill="x", padx=8, pady=4)

        self.playlist_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="Скачать весь плейлист (если ссылка - плейлист)",
                         variable=self.playlist_var).pack(side="left")

        row3 = ttk.Frame(options_frame)
        row3.pack(fill="x", padx=8, pady=4)

        self.subs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Скачать субтитры, языки:",
                         variable=self.subs_var).pack(side="left")
        self.subs_lang_var = tk.StringVar(value="ru,en")
        subs_entry = ttk.Entry(row3, textvariable=self.subs_lang_var, width=12)
        subs_entry.pack(side="left", padx=(4, 0))
        self._add_context_menu(subs_entry)

        row4 = ttk.Frame(options_frame)
        row4.pack(fill="x", padx=8, pady=4)
        ttk.Label(row4, text="Cookies из браузера (если YouTube просит войти):").pack(side="left")
        self.browser_var = tk.StringVar(value="Chrome" if "Chrome" in BROWSERS else BROWSERS[0])
        ttk.Combobox(row4, textvariable=self.browser_var, values=BROWSERS,
                     state="readonly", width=12).pack(side="left", padx=(4, 0))

        out_frame = ttk.Frame(self.root)
        out_frame.pack(fill="x", **pad)
        ttk.Label(out_frame, text="Папка для сохранения:").pack(anchor="w")
        path_row = ttk.Frame(out_frame)
        path_row.pack(fill="x", pady=(2, 0))
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        output_entry = ttk.Entry(path_row, textvariable=self.output_var)
        output_entry.pack(side="left", fill="x", expand=True)
        self._add_context_menu(output_entry)
        ttk.Button(path_row, text="Обзор...", command=self._choose_folder).pack(side="left", padx=(6, 0))

        btn_row = ttk.Frame(self.root)
        btn_row.pack(fill="x", **pad)
        self.download_btn = ttk.Button(btn_row, text="Скачать", command=self._start_download)
        self.download_btn.pack(side="left")
        self.cancel_btn = ttk.Button(btn_row, text="Отмена", command=self._cancel_download, state="disabled")
        self.cancel_btn.pack(side="left", padx=(6, 0))

        self.progress = ttk.Progressbar(self.root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self.root, textvariable=self.status_var).pack(anchor="w", padx=10)

        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._on_mode_change()

    def _on_mode_change(self):
        if self.mode_var.get() == "audio":
            self.quality_combo.configure(state="disabled")
        else:
            self.quality_combo.configure(state="readonly")

    def _add_context_menu(self, entry):
        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label="Вырезать", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Копировать", command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="Вставить", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: entry.select_range(0, "end"))

        def show_menu(event):
            entry.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        entry.bind("<Button-3>", show_menu)

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
        if folder:
            self.output_var.set(folder)

    def _check_ffmpeg(self):
        if FFMPEG_PATH is None:
            self._log(
                "Внимание: ffmpeg не найден. Он нужен для склейки видео+аудио "
                "и для конвертации в mp3. Установите его: winget install ffmpeg "
                "(затем перезапустите программу)."
            )
        if DENO_PATH is None:
            self._log(
                "Внимание: Deno не найден. Он нужен, чтобы решать JS-проверки YouTube. "
                "Установите: winget install DenoLand.Deno (затем перезапустите программу)."
            )

    # ---------- logging / progress ----------

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, text):
        self.status_var.set(text)

    # ---------- download ----------

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Нет ссылки", "Вставьте ссылку на видео или плейлист YouTube.")
            return

        output_dir = self.output_var.get().strip() or DEFAULT_OUTPUT_DIR
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Ошибка папки", f"Не удалось создать папку:\n{exc}")
            return

        if self.mode_var.get() == "video" and FFMPEG_PATH is None:
            if not messagebox.askyesno(
                "ffmpeg не найден",
                "ffmpeg не установлен. Без него видео и аудио могут не склеиться "
                "в один файл. Продолжить всё равно?",
            ):
                return

        self.cancel_requested = False
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress.configure(value=0)
        self._set_status("Подготовка...")

        self.download_thread = threading.Thread(
            target=self._run_download, args=(url, output_dir), daemon=True
        )
        self.download_thread.start()

    def _cancel_download(self):
        self.cancel_requested = True
        self._set_status("Отмена...")

    def _progress_hook(self, d):
        if self.cancel_requested:
            raise KeyboardInterrupt("Скачивание отменено пользователем")

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                pct = downloaded / total * 100
                self.root.after(0, self.progress.configure, {"value": pct})
            filename = os.path.basename(d.get("filename", ""))
            speed = d.get("speed")
            speed_str = f"{speed / 1024 / 1024:.2f} МБ/с" if speed else "..."
            self.root.after(0, self._set_status, f"Скачивание: {filename} ({speed_str})")
        elif d["status"] == "finished":
            self.root.after(0, self._set_status, "Обработка файла...")
            self.root.after(0, self.progress.configure, {"value": 100})

    def _build_opts(self, output_dir):
        mode = self.mode_var.get()
        quality = self.quality_var.get()

        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

        opts = {
            "outtmpl": outtmpl,
            "noplaylist": not self.playlist_var.get(),
            "progress_hooks": [self._progress_hook],
            "logger": TkLogger(self._log),
            "restrictfilenames": False,
            "quiet": True,
            "no_warnings": False,
        }

        if FFMPEG_PATH:
            opts["ffmpeg_location"] = FFMPEG_PATH
        if DENO_PATH:
            opts["js_runtimes"] = [f"deno:{DENO_PATH}"]

        browser = self.browser_var.get()
        if browser in BROWSER_KEYS:
            opts["cookiesfrombrowser"] = (BROWSER_KEYS[browser],)

        if mode == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            if quality == "Лучшее":
                opts["format"] = "bestvideo+bestaudio/best"
            else:
                height = QUALITY_HEIGHT[quality]
                opts["format"] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            opts["merge_output_format"] = "mp4"

        if self.subs_var.get():
            langs = [lang.strip() for lang in self.subs_lang_var.get().split(",") if lang.strip()]
            if langs:
                opts["writesubtitles"] = True
                opts["writeautomaticsub"] = True
                opts["subtitleslangs"] = langs
                opts["subtitlesformat"] = "srt/best"

        return opts

    def _run_download(self, url, output_dir):
        opts = self._build_opts(output_dir)
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            if not self.cancel_requested:
                self.root.after(0, self._set_status, "Готово")
                self.root.after(0, self._log, "Скачивание завершено успешно.")
        except KeyboardInterrupt:
            self.root.after(0, self._set_status, "Отменено")
            self.root.after(0, self._log, "Скачивание отменено пользователем.")
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, self._set_status, "Ошибка")
            self.root.after(0, self._log, f"Ошибка: {exc}")
            self.root.after(0, messagebox.showerror, "Ошибка скачивания", str(exc))
        finally:
            self.root.after(0, self.download_btn.configure, {"state": "normal"})
            self.root.after(0, self.cancel_btn.configure, {"state": "disabled"})


class TkLogger:
    """Adapts yt-dlp's logger interface to the app's log widget."""

    def __init__(self, log_func):
        self._log = log_func

    def debug(self, msg):
        if msg.startswith("[debug] "):
            return
        self._log(msg)

    def info(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(f"Предупреждение: {msg}")

    def error(self, msg):
        self._log(f"Ошибка: {msg}")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
