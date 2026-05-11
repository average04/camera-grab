# camera-grab

A tiny Python/OpenCV camera preview for using a Canon mirrorless camera as a
Windows camera source.

This app assumes Windows already exposes the Canon feed as a camera device. For
most Canon mirrorless setups, install and run Canon EOS Webcam Utility or the
Canon app that provides the video source, then select that device here by index.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Find the Camera

```powershell
python camera_grab.py --scan
```

If your Canon is not index `0`, use the index shown by the scan:

```powershell
python camera_grab.py --index 1
```

DirectShow is the default backend because it is usually the most reliable on
Windows. If a source does not open, try:

```powershell
python camera_grab.py --backend msmf --scan
python camera_grab.py --backend auto --scan
```

## Preview Controls

- `S`: save a snapshot to `captures/`
- `M`: toggle mirrored preview
- `Q` or `Esc`: quit

## Examples

```powershell
python camera_grab.py --index 1 --width 1280 --height 720
python camera_grab.py --index 1 --mirror
```
