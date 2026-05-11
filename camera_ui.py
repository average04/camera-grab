from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from camera_grab import (
    camera_backend,
    get_directshow_devices,
    get_windows_camera_devices,
    import_cv2,
    open_camera,
    save_snapshot,
    scan_cameras,
)


@dataclass(frozen=True)
class CameraSource:
    index: int
    name: str
    opens: bool

    @property
    def label(self) -> str:
        status = "ready" if self.opens else "listed"
        return f"{self.index}: {self.name} ({status})"


class CameraGrabUi:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cv2 = import_cv2()
        self.capture = None
        self.frame = None
        self.photo = None
        self.sources: list[CameraSource] = []

        self.backend_var = tk.StringVar(value="dshow")
        self.manual_index_var = tk.StringVar(value="0")
        self.mirror_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Choose a camera source.")
        self.windows_devices_var = tk.StringVar(value="")

        self.root.title("Camera Grab")
        self.root.geometry("980x640")
        self.root.minsize(780, 520)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()
        self.refresh_sources()

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Status.TLabel", foreground="#475569")

        sidebar = ttk.Frame(self.root, padding=16)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.columnconfigure(0, weight=1)

        title = ttk.Label(sidebar, text="Camera Sources", style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        backend_row = ttk.Frame(sidebar)
        backend_row.grid(row=1, column=0, sticky="ew", pady=(16, 8))
        backend_row.columnconfigure(1, weight=1)

        ttk.Label(backend_row, text="Backend").grid(row=0, column=0, sticky="w")
        backend = ttk.Combobox(
            backend_row,
            textvariable=self.backend_var,
            values=("dshow", "msmf", "auto"),
            state="readonly",
            width=10,
        )
        backend.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        backend.bind("<<ComboboxSelected>>", lambda _event: self.refresh_sources())

        self.source_list = tk.Listbox(
            sidebar,
            width=34,
            height=14,
            activestyle="none",
            exportselection=False,
        )
        self.source_list.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        self.source_list.bind("<Double-Button-1>", lambda _event: self.start_preview())
        sidebar.rowconfigure(2, weight=1)

        actions = ttk.Frame(sidebar)
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)

        ttk.Button(actions, text="Refresh", command=self.refresh_sources).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions, text="Start", command=self.start_preview).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Button(actions, text="Stop", command=self.stop_preview).grid(
            row=1, column=0, sticky="ew", pady=(10, 0), padx=(0, 6)
        )
        ttk.Button(actions, text="Snapshot", command=self.take_snapshot).grid(
            row=1, column=1, sticky="ew", pady=(10, 0), padx=(6, 0)
        )

        manual = ttk.Frame(sidebar)
        manual.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        manual.columnconfigure(1, weight=1)

        ttk.Label(manual, text="Manual index").grid(row=0, column=0, sticky="w")
        ttk.Entry(manual, textvariable=self.manual_index_var, width=8).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(manual, text="Try", command=self.start_manual_preview).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Checkbutton(
            sidebar,
            text="Mirror preview",
            variable=self.mirror_var,
        ).grid(row=5, column=0, sticky="w", pady=(14, 0))

        ttk.Label(
            sidebar,
            textvariable=self.status_var,
            style="Status.TLabel",
            wraplength=260,
        ).grid(row=6, column=0, sticky="ew", pady=(16, 0))

        ttk.Label(
            sidebar,
            textvariable=self.windows_devices_var,
            style="Status.TLabel",
            wraplength=260,
        ).grid(row=7, column=0, sticky="ew", pady=(12, 0))

        preview_area = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        preview_area.grid(row=0, column=1, sticky="nsew")
        preview_area.columnconfigure(0, weight=1)
        preview_area.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(
            preview_area,
            text="No camera preview",
            anchor="center",
            background="#111827",
            foreground="#e5e7eb",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")

    def refresh_sources(self) -> None:
        self.stop_preview()
        backend = camera_backend(self.cv2, self.backend_var.get())
        open_indices = scan_cameras(self.cv2, backend, 20)
        device_names = self.get_device_names()
        windows_devices = get_windows_camera_devices()

        sources: list[CameraSource] = []
        max_index = max(len(device_names), max(open_indices, default=-1) + 1)

        for index in range(max_index):
            name = device_names[index] if index < len(device_names) else f"Camera {index}"
            sources.append(CameraSource(index, name, index in open_indices))

        self.sources = sources
        self.source_list.delete(0, tk.END)

        for source in self.sources:
            self.source_list.insert(tk.END, source.label)

        if windows_devices:
            self.windows_devices_var.set(
                "Windows sees: " + "; ".join(windows_devices[:4])
            )
        else:
            self.windows_devices_var.set("")

        canon_index = self.find_canon_index()
        if canon_index is not None:
            self.source_list.selection_set(canon_index)
            self.source_list.activate(canon_index)
            self.manual_index_var.set(str(self.sources[canon_index].index))
            self.status_var.set("Canon source detected. Press Start to preview it.")
        elif self.sources:
            self.source_list.selection_set(0)
            self.source_list.activate(0)
            self.manual_index_var.set(str(self.sources[0].index))
            self.status_var.set(
                "Canon was not named directly. Try ready sources, or use Manual index."
            )
        else:
            self.status_var.set(
                "No OpenCV sources found. Start Canon EOS Webcam Utility, then Refresh."
            )

    def get_device_names(self) -> list[str]:
        if self.backend_var.get() != "dshow":
            return []

        try:
            return get_directshow_devices()
        except SystemExit:
            messagebox.showerror(
                "Missing dependency",
                "Install dependencies with: python -m pip install -r requirements.txt",
            )
            return []

    def find_canon_index(self) -> int | None:
        canon_terms = ("canon", "eos", "webcam utility", "usb video", "capture")
        for list_index, source in enumerate(self.sources):
            name = source.name.casefold()
            if any(term in name for term in canon_terms):
                return list_index
        return None

    def selected_source(self) -> CameraSource | None:
        selected = self.source_list.curselection()
        if not selected:
            return None
        return self.sources[selected[0]]

    def start_manual_preview(self) -> None:
        try:
            index = int(self.manual_index_var.get())
        except ValueError:
            messagebox.showerror("Invalid index", "Enter a whole-number camera index.")
            return

        self.start_preview_for_index(index, f"Camera {index}")

    def start_preview(self) -> None:
        source = self.selected_source()
        if source is None:
            messagebox.showinfo("No source selected", "Choose a camera source first.")
            return

        self.manual_index_var.set(str(source.index))
        self.start_preview_for_index(source.index, source.name)

    def start_preview_for_index(self, index: int, name: str) -> None:
        self.stop_preview()
        backend = camera_backend(self.cv2, self.backend_var.get())
        self.capture = open_camera(self.cv2, index, backend, 1280, 720)
        if self.capture is None:
            self.status_var.set(f"Could not open {name}.")
            messagebox.showerror("Camera unavailable", f"Could not open index {index}.")
            return

        self.status_var.set(f"Previewing {name}.")
        self.update_preview()

    def stop_preview(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.frame = None
        self.preview_label.configure(image="", text="No camera preview")

    def update_preview(self) -> None:
        if self.capture is None:
            return

        ok, frame = self.capture.read()
        if not ok:
            self.status_var.set("Camera stopped returning frames.")
            self.stop_preview()
            return

        if self.mirror_var.get():
            frame = self.cv2.flip(frame, 1)

        self.frame = frame
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail(self.preview_size(), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.photo, text="")
        self.root.after(15, self.update_preview)

    def preview_size(self) -> tuple[int, int]:
        width = max(self.preview_label.winfo_width(), 320)
        height = max(self.preview_label.winfo_height(), 240)
        return width, height

    def take_snapshot(self) -> None:
        if self.frame is None:
            messagebox.showinfo("No frame", "Start a preview before saving a snapshot.")
            return

        path = save_snapshot(self.frame, Path("captures"))
        self.cv2.imwrite(str(path), self.frame)
        self.status_var.set(f"Saved {path}")

    def on_close(self) -> None:
        self.stop_preview()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    CameraGrabUi(root)
    root.mainloop()


if __name__ == "__main__":
    main()
