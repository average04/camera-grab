from __future__ import annotations

import argparse
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


def save_snapshot(frame, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / f"snapshot-{stamp}.jpg"


def run_preview(args: argparse.Namespace) -> int:
    cv2 = import_cv2()
    backend = camera_backend(cv2, args.backend)

    if args.scan:
        cameras = scan_cameras(cv2, backend, args.scan_limit)
        if cameras:
            print("Available camera indices:", ", ".join(str(i) for i in cameras))
        else:
            print("No camera sources were found.")
        return 0

    cap = open_camera(cv2, args.index, backend, args.width, args.height)
    if cap is None:
        print(
            f"Could not open camera index {args.index}. Try scanning with:\n\n"
            f"  python camera_grab.py --scan --backend {args.backend}\n",
            file=sys.stderr,
        )
        return 1

    print("Preview controls: S = snapshot, M = mirror, Q/Esc = quit")
    mirror = args.mirror
    window_name = f"Camera Grab - index {args.index}"

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
        "-i",
        "--index",
        type=int,
        default=0,
        help="Camera index to open. Default: 0.",
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
        "--scan",
        action="store_true",
        help="Scan for available camera indices and exit.",
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
    return run_preview(args)


if __name__ == "__main__":
    raise SystemExit(main())
