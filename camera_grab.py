from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def import_cv2():
    try:
        import cv2
    except ImportError:
        print(
            "OpenCV is not installed yet. Run:\n\n"
            "  python -m pip install -r requirements.txt\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return cv2


def get_directshow_devices() -> list[str]:
    try:
        from pygrabber.dshow_graph import FilterGraph
    except ImportError:
        print(
            "Camera name listing needs pygrabber. Run:\n\n"
            "  python -m pip install -r requirements.txt\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return FilterGraph().get_input_devices()


def get_windows_camera_devices() -> list[str]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-PnpDevice -Class Camera,Image -PresentOnly | "
        "Select-Object -ExpandProperty FriendlyName",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def camera_backend(cv2, requested: str):
    if requested == "auto":
        return cv2.CAP_ANY
    if requested == "dshow":
        return cv2.CAP_DSHOW
    if requested == "msmf":
        return cv2.CAP_MSMF
    raise ValueError(f"Unsupported backend: {requested}")


def open_camera(cv2, index: int, backend: int, width: int | None, height: int | None):
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        return None

    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    ok, _ = cap.read()
    if not ok:
        cap.release()
        return None

    return cap


def scan_cameras(cv2, backend: int, limit: int) -> list[int]:
    found: list[int] = []
    for index in range(limit):
        cap = open_camera(cv2, index, backend, None, None)
        if cap is None:
            continue

        found.append(index)
        cap.release()

    return found


def print_camera_sources(devices: list[str], open_indices: list[int]) -> None:
    if devices:
        print("DirectShow camera sources:")
        for index, name in enumerate(devices):
            status = "opens" if index in open_indices else "listed"
            print(f"  {index}: {name} ({status})")
        return

    if open_indices:
        print("Available camera indices:", ", ".join(str(i) for i in open_indices))
    else:
        print("No camera sources were found.")


def resolve_camera_index(args: argparse.Namespace) -> int:
    if not args.name:
        return args.index

    devices = get_directshow_devices()
    query = args.name.casefold()
    matches = [
        (index, name)
        for index, name in enumerate(devices)
        if query in name.casefold()
    ]

    if not matches:
        print(f"No camera source name contains {args.name!r}.", file=sys.stderr)
        if devices:
            print("Available sources:", file=sys.stderr)
            for index, name in enumerate(devices):
                print(f"  {index}: {name}", file=sys.stderr)
        return -1

    index, name = matches[0]
    if len(matches) > 1:
        print(f"Multiple matches found; using {index}: {name}")
    else:
        print(f"Using {index}: {name}")
    return index


def save_snapshot(frame, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / f"snapshot-{stamp}.jpg"


def run_preview(args: argparse.Namespace) -> int:
    cv2 = import_cv2()
    backend = camera_backend(cv2, args.backend)

    if args.list:
        devices = get_directshow_devices() if args.backend == "dshow" else []
        cameras = scan_cameras(cv2, backend, args.scan_limit)
        print_camera_sources(devices, cameras)
        return 0

    index = resolve_camera_index(args)
    if index < 0:
        return 1

    cap = open_camera(cv2, index, backend, args.width, args.height)
    if cap is None:
        print(
            f"Could not open camera index {index}. Try listing sources with:\n\n"
            f"  python camera_grab.py --list --backend {args.backend}\n",
            file=sys.stderr,
        )
        return 1

    print("Preview controls: S = snapshot, M = mirror, Q/Esc = quit")
    mirror = args.mirror
    window_name = f"Camera Grab - index {index}"

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera stopped returning frames.", file=sys.stderr)
                return 1

            if mirror:
                frame = cv2.flip(frame, 1)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                return 0
            if key == ord("m"):
                mirror = not mirror
            if key == ord("s"):
                path = save_snapshot(frame, args.output)
                cv2.imwrite(str(path), frame)
                print(f"Saved {path}")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview a Windows camera source, such as Canon EOS Webcam Utility."
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Open the desktop camera source picker UI.",
    )
    parser.add_argument(
        "-i",
        "--index",
        type=int,
        default=0,
        help="Camera index to open when --name is not used. Default: 0.",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="Open the first DirectShow camera source whose name contains this text.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "dshow", "msmf"),
        default="dshow",
        help="OpenCV capture backend. DirectShow is often best on Windows. Default: dshow.",
    )
    parser.add_argument("--width", type=int, help="Requested capture width.")
    parser.add_argument("--height", type=int, help="Requested capture height.")
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Start with a horizontally mirrored preview.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("captures"),
        help="Directory for snapshots. Default: captures.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available camera sources and exit.",
    )
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=10,
        help="Number of camera indices to try while scanning. Default: 10.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.ui:
        from camera_ui import main as ui_main

        ui_main()
        return 0

    return run_preview(args)


if __name__ == "__main__":
    raise SystemExit(main())
