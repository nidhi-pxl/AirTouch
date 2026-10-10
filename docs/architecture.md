# AirTouch Architecture

## Pipeline
Webcam frame → hand tracker → gesture recognition / temporal detectors → action mapper → event logger.

## Module contracts
- Hand tracker: frame in; structured landmarks and metadata out.
- Recognizer: landmarks/finger states in; standardized label or `UNKNOWN`.
- Pinch detector: hand data in; state/transition out.
- Swipe detector: recent positions over time in; `SWIPE_LEFT`, `SWIPE_RIGHT`, or no event.
- Action mapper: gesture event in; action and feedback out.
- Event logger: structured event record in; persistent row out.

## Decisions to finalize
- Exact gesture-to-action mapping.
- Event schema and timestamp units.
- Safe/dry-run mode for desktop actions.
- Calibration implementation and data retention.
- Behaviour when no hand or an unknown gesture is detected.
