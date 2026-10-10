# AirTouch
## Fine-Grained Finger Gesture Interaction Using Commodity Camera Sensing

AirTouch is an HCI project exploring whether a standard laptop webcam can support usable fine-grained finger-gesture interaction for simple desktop tasks without specialized wearable hardware. **This repository is an initial scaffold; placeholders are not completed functionality.**

## Research question
Can a camera-based, fine-grained finger-gesture interface provide an effective and usable alternative to conventional mouse interaction for simple desktop tasks?

## Proposed gesture families
- Point → select
- Pinch → zoom
- Open hand → scroll

Confirm exact mappings before implementation. Swipe directions may be separate event labels within one gesture family.

## Pipeline
Webcam/OpenCV → MediaPipe hand landmarks → gesture recognition and temporal detectors → action mapping and feedback → event logging → analysis.

## Setup
Recommended: Python 3.11 or 3.12 because MediaPipe wheel support varies by Python version/platform.

Windows PowerShell:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
macOS/Linux:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The app entry point is a scaffold until implemented. Intended command: `python -m src.main`.

## Roles
- **Nidhi:** hand tracking, integration, `src/main.py`, repository setup and root config.
- **Person 1:** action mapping, gestures.
- **Person 2:** gesture recognition, detection.
- **Person 3:** HCI study protocol and research documentation/ questionnaire.
- **Person 4:** event logging, analysis and evaluation outputs.


## Module contracts
- Tracker: frame in → structured landmarks/metadata or no hand.
- Recognizer: landmarks/finger states in → standardized label or `UNKNOWN`.
- Pinch detector: hand data in → pinch state/transition.
- Swipe detector: recent positions over time → swipe direction or no event.
- Action mapper: gesture event in → action and feedback.
- Event logger: structured record in → saved row.

Suggested labels: `POINT`, `PINCH`, `SWIPE_LEFT`, `SWIPE_RIGHT`, `OPEN_HAND`, `FIST`, `UNKNOWN`.

## Development rules
1. Keep `main` runnable; use feature branches and pull requests.
2. One primary owner per module; coordinate before editing another person's file.
3. Never commit `.venv`, local logs, secrets or identifiable participant data.
4. Use synthetic records to test analysis before real data exists.
5. Label pilot data as pilot data; don't present planned features/results as completed.
6. Confirm course requirements before participant testing.

## Evaluation plan
The proposal plans a within-subject comparison of Mouse Only, Gesture without Calibration, and Gesture with Calibration, with at least 12 participants. Measures include recognition accuracy, false-positive rate, latency, task completion time, errors/attempts, confusion matrix, SUS, ease, workload, comfort, satisfaction, preference and qualitative feedback.
