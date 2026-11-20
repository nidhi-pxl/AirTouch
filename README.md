# AirTouch

### Fine-Grained Finger Gesture Interaction Using Commodity Camera Sensing

AirTouch is a webcam-based desktop gesture-control application developed as part of a Human-Computer Interaction (HCI) project.

It explores whether a standard laptop webcam can support fine-grained finger-gesture interaction for everyday desktop tasks without requiring specialized wearable hardware.

Using **OpenCV**, **MediaPipe**, and **PyAutoGUI**, AirTouch tracks hand landmarks, recognizes gestures, and translates them into desktop actions such as cursor movement, clicking, scrolling, zooming, and undoing.

The application features a modern desktop interface built with **PySide6**, providing live camera preview and controls to start, pause, resume, and stop gesture interaction.

## Features

- Real-time webcam-based hand tracking.
- Finger landmark detection using MediaPipe.
- Gesture-based desktop cursor control.
- Left-click and right-click interactions.
- Gesture-based scrolling and zooming.
- Undo gesture support.
- Live camera preview.
- Start, Pause, Resume, and Stop controls.
- Gesture status and last recognized action display.
- Smooth camera preview fade-out when stopped.
- Local webcam processing.

## Implemented Gestures

| Gesture | Desktop Action |
|---|---|
| Index finger extended, other fingers closed | Cursor movement |
| Open palm followed by index finger bend | Left click |
| Pinky gesture | Right click |
| Thumb movement to the right | Zoom in |
| Index and middle fingers extended, swipe left | Zoom out |
| Swipe gesture | Scroll |
| Thumbs down | Undo |

Gesture detection uses hand landmarks, movement tracking, temporal detection, and confirmation frames where applicable.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| OpenCV | Webcam capture and image processing |
| MediaPipe | Hand landmark detection |
| PyAutoGUI | Desktop interaction |
| PySide6 | Desktop graphical interface |
| PyInstaller | Standalone application packaging |

## Application Architecture

```text
AirTouch/
│
├── src/
│   ├── main.py
│   │
│   ├── vision/
│   │   └── hand_tracker.py
│   │
│   ├── gestures/
│   │   ├── swipe_detector.py
│   │   ├── zoom_detector.py
│   │   ├── pinky_detector.py
│   │   └── thumbs_down_detector.py
│   │
│   ├── interaction/
│   │   ├── action_mapper.py
│   │   └── feedback.py
│   │
│   ├── logging/
│   │   └── event_logger.py
│   │
│   └── gui/
│       ├── main_window.py
│       └── camera_worker.py
│
├── requirements.txt
├── requirements-ui.txt
├── project_description.md
├── README.md
└── .gitignore
```

### Processing Pipeline

```text
Webcam Input
     |
     v
OpenCV Frame Capture
     |
     v
MediaPipe Hand Tracking
     |
     v
Hand Landmark Extraction
     |
     v
Gesture Detection
     |
     v
Action Mapping
     |
     v
Desktop Interaction
```

The camera-processing loop runs separately from the graphical interface using a worker thread, keeping the application responsive during gesture recognition.

## Quick Start

### Prerequisites

- Windows 10 or later for the current desktop application workflow.
- Python 3.11 or 3.12 recommended.
- A working webcam.

```

### Run AirTouch

From the project root:

```powershell
python -m src.main
```

The AirTouch desktop application will open and allow you to control your computer using hand gestures.

## Application Controls

| Control | Function |
|---|---|
| Start AirTouch | Starts webcam capture and gesture recognition |
| Pause | Temporarily pauses gesture processing |
| Resume | Resumes gesture processing |
| Stop | Stops camera processing and displays the stopped screen |

The interface displays the live camera feed, current processing status, and last recognized action.

## Project Documentation

See [project_description.md](project_description.md) for detailed installation, packaging, and distribution instructions.

## Privacy

AirTouch processes webcam input locally on the user's computer. Camera frames are used for real-time hand tracking and gesture recognition.

Any additional data collection for research or evaluation purposes are documented separately.

## Limitations

- Requires a functioning webcam.
- Recognition performance can vary with lighting, camera quality, and hand visibility.
- Hand occlusion and positioning may affect gesture recognition.
- The current desktop application workflow targets Windows.
- Desktop actions may behave differently depending on the operating system and application in focus.

## License

This project was developed as part of an academic Human-Computer Interaction course project. Add an appropriate open-source license before accepting external contributions or redistributing the project.