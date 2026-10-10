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

## Folder Structure
File/folder	                    Purpose
src/main.py	                    Starts the webcam pipeline and connects all modules.
vision/hand_tracker.py	        Detects hands and provides landmark coordinates.
gestures/recognizer.py	        Recognizes static gestures such as pointing, open hand and fist.
gestures/pinch_detector.py	    Detects a pinch and its start/release.
gestures/swipe_detector.py	    Detects a swipe from movement over time.
interaction/action_mapper.py	Maps recognized gestures to desktop actions.
interaction/feedback.py	        Displays the detected gesture/action and useful status messages.
logging/event_logger.py	        Records timestamps, predictions, latency, action outcomes and errors.
tests/	                        Checks the modules and whether the pipeline works together.
study/	                        Holds the procedure, participant instructions and questionnaire.
analysis/analyze_results.py	    Calculates metrics and produces plots from collected data.
data/	                        Input data or approved study data, if any.
results/	                    Generated CSVs, plots and evaluation outputs.
docs/	                        Explains the architecture and research inspiration.