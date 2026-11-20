# AirTouch — Project Description

## Short Description

AirTouch is a webcam-based finger-gesture interface exploring whether commodity camera sensing can support usable fine-grained desktop interaction without dedicated wearable hardware.

The project combines computer vision, hand landmark tracking, gesture recognition, and desktop action mapping into a standalone desktop application.

The application uses a standard webcam to track hand movements and translate recognized gestures into desktop interactions. A PySide6-based graphical interface provides live camera preview and controls for managing gesture interaction.

## Problem

Traditional desktop interaction relies heavily on physical input devices such as a mouse and keyboard. Gesture interaction may offer a more direct and accessible input modality, but subtle or closely related finger movements can be difficult to distinguish reliably.

AirTouch investigates whether a standard laptop webcam can recognize a small gesture vocabulary accurately enough to support simple desktop tasks.

## Motivation

The project explores an accessible approach to gesture-based interaction using hardware that users may already own.

It also investigates whether short per-user calibration can improve gesture recognition and user experience compared with generic recognition.

## Proposed Approach

AirTouch uses a webcam to capture hand movements and MediaPipe to extract hand landmarks. These landmarks are processed by gesture-specific detection modules, which recognize gestures and generate events.

The events are passed to an action-mapping module that translates recognized gestures into desktop actions.

The current implementation supports:

- Cursor movement.
- Left click.
- Right click.
- Zoom in and zoom out.
- Scrolling.
- Undo.

The desktop interface provides live camera preview, gesture status, and controls to start, pause, resume, and stop the application.

The original research proposal considered gesture families such as point, pinch, swipe, open hand, and fist. The implemented gesture mappings have evolved during development.

## Research Question

Can a camera-based, fine-grained finger-gesture interface provide an effective and usable alternative to conventional mouse interaction for simple desktop tasks?

## Evaluation

The proposed within-subject study compares three interaction conditions:

1. **Mouse Only:** Conventional mouse-based interaction.
2. **Gesture without Calibration:** Gesture interaction without user-specific calibration.
3. **Gesture with Calibration:** Gesture interaction with user-specific calibration.

The proposal specifies at least 12 participants.

### Evaluation Measures

- Gesture recognition accuracy.
- False-positive rate.
- Recognition latency.
- Task completion time.
- Errors and number of attempts.
- Confusion matrix.
- System Usability Scale (SUS).
- Ease of use.
- Workload and comfort.
- User satisfaction and preference.
- Qualitative feedback.

The evaluation aims to investigate the usability and effectiveness of webcam-based fine-grained gesture interaction compared with conventional mouse interaction.

## Research Inspiration

Liu, Y., Jiang, F., & Gowda, M. (2020). "Finger Gesture Tracking for Interactive Applications: A Pilot Study with Sign Languages (FinGTrAC)." IMWUT 2020.

https://doi.org/10.1145/3414117

AirTouch adapts the broad idea of fine-grained gesture interaction to commodity camera-based sensing. It is inspired by this work, not a reproduction of its wearable sensing system.

## Expected Deliverables

- Runnable webcam-based hand-tracking application.
- Recognition for the implemented gesture vocabulary.
- Gesture-to-action mapping and visible feedback.
- Generic and calibrated recognition conditions, to the extent implemented and tested.
- Event logging and analysis scripts.
- Documented study protocol.
- Evaluation results.

---

# Installation and Setup

## Prerequisites

- Windows 10 or later for the current desktop application workflow.
- Python 3.11 or 3.12 recommended for dependency compatibility.
- A working webcam.
- Internet access for installing dependencies.

Python 3.11 or 3.12 is recommended because MediaPipe wheel support can vary across Python versions and platforms.

## 1. Clone the Repository

```powershell
git clone <REPOSITORY_URL>
cd AirTouch
```

Replace `<REPOSITORY_URL>` with the actual GitHub repository URL.

## 2. Create a Virtual Environment

```powershell
py -3.11 -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the core dependencies:

```powershell
pip install -r requirements.txt
```

Install the desktop GUI and packaging dependencies:

```powershell
pip install -r requirements-ui.txt
```

## 4. Run the Application

From the project root:

```powershell
python -m src.main
```

The AirTouch desktop interface will open.

Make sure the webcam is connected and available to the application.

---

# Running Without Python (Windows Executable)

AirTouch can be packaged into a standalone Windows application using PyInstaller.

This allows external users to run AirTouch without manually installing Python, creating a virtual environment, or installing project dependencies.

## 1. Install PyInstaller

If it is not already installed:

```powershell
pip install pyinstaller
```

## 2. Build the Application

Run the following command from the project root:

```powershell
python -m PyInstaller --noconfirm --clean --windowed --onedir --name AirTouch --collect-all PySide6 --collect-all cv2 --collect-all mediapipe src/main.py
```

### Build Options

- `--noconfirm`: Overwrites previous build output without prompting.
- `--clean`: Cleans temporary build files.
- `--windowed`: Runs the application without opening a console window.
- `--onedir`: Packages the application and its dependencies into a directory.
- `--name AirTouch`: Sets the application name.
- `--collect-all`: Includes package data and supporting files for the specified libraries.

## 3. Locate the Executable

After a successful build, the output will be generated inside:

```text
dist/
└── AirTouch/
    ├── AirTouch.exe
    └── _internal/
```

The executable can be launched by opening:

```text
dist/AirTouch/AirTouch.exe
```

The entire application folder must be retained because the executable depends on the packaged files and libraries inside `_internal`.

---


## Instructions for External Users

Users can access AirTouch by:

1. Downloading the ZIP archive from GitHub Releases.
2. Extracting the archive.
3. Opening the extracted `AirTouch` folder.
4. Double-clicking `AirTouch.exe`.
5. Connecting or allowing access to a working webcam.
6. Selecting **Start AirTouch** to begin gesture interaction.

Users do not need to install Python or the project's dependencies separately.

Windows may display a SmartScreen warning for an unsigned executable.

## Future Distribution Improvements

- Create a dedicated mac installer.
- Provide desktop and Start Menu shortcuts.
- Add version information.
- Consider code signing.
- Provide installation and troubleshooting instructions.

---

# Development Guidelines

1. Keep the main application runnable.
2. Use feature branches for individual contributions.
3. Coordinate before editing another contributor's module.
4. Keep vision, gesture detection, interaction, GUI, and logging logic modular.
5. Never commit `.venv`, local logs, secrets, or identifiable participant data.
6. Test individual modules before integrating changes.
7. Use synthetic records to test analysis before real data exists.
8. Label pilot data as pilot data.
9. Do not present planned features or results as completed functionality.
10. Confirm course requirements before conducting participant testing.

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `hand_tracker.py` | Captures hand landmarks from webcam frames. |
| Gesture detector modules | Recognize specific hand gestures and movement patterns. |
| `action_mapper.py` | Converts recognized gesture events into desktop actions. |
| `feedback.py` | Handles interaction feedback. |
| `camera_worker.py` | Runs camera processing separately from the GUI. |
| `main_window.py` | Provides the desktop interface and application controls. |
| `event_logger.py` | Handles structured event logging. |
| `main.py` | Application entry point and shared helper functions. |

---


# Future Improvements

- User-specific gesture calibration.
- Additional customizable gestures.
- Improved recognition accuracy and robustness.
- Configurable gesture-to-action mappings.
- Enhanced visual and audio feedback.
- Improved handling of hand occlusion and varying lighting conditions.
- Cross-platform desktop support.
- Dedicated application installer and icon.
- Expanded usability testing and performance evaluation.
- Improved event logging and analysis tools.

---

# Project Status

AirTouch has progressed from an initial research scaffold to a working webcam-based desktop gesture-control application with a graphical interface.

The project continues to explore the usability and effectiveness of fine-grained finger gestures as an alternative input modality for simple desktop interactions.