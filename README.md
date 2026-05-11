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

For the desktop UI:

```powershell
python camera_grab.py --ui
```

The UI lists available sources, auto-selects the first Canon/EOS source it can
find, and previews the selected camera.

On Windows, you can also double-click `camera-ui.bat`.

If the Canon camera is not named directly, look for sources like `EOS Webcam
Utility`, `USB Video Device`, or a generic `Camera 1`. Select each ready source
and press `Start`, or use the manual index box.

For the command line:

```powershell
python camera_grab.py --list
```

To open the Canon source by name:

```powershell
python camera_grab.py --name Canon
```

If you see more than one Canon-related source, use the exact index shown by the
list:

```powershell
python camera_grab.py --index 1
```

DirectShow is the default backend because it is usually the most reliable on
Windows. If a source does not open, try:

```powershell
python camera_grab.py --backend msmf --list
python camera_grab.py --backend auto --list
```

## Preview Controls

- `S`: save a snapshot to `captures/`
- `M`: toggle mirrored preview
- `Q` or `Esc`: quit

## Examples

```powershell
python camera_grab.py --name Canon --width 1280 --height 720
python camera_grab.py --index 1 --width 1280 --height 720
python camera_grab.py --index 1 --mirror
```
