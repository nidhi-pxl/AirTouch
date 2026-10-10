# AirTouch — Project Description

## Short description
AirTouch is a webcam-based finger-gesture interface exploring whether commodity camera sensing can support usable fine-grained desktop interaction without dedicated wearable hardware.

## Problem
Traditional desktop interaction relies heavily on physical input devices. Gesture interaction may offer a direct input modality, but subtle or closely related finger movements can be difficult to distinguish reliably. AirTouch investigates whether a standard laptop webcam can recognize a small gesture vocabulary well enough for simple desktop tasks.

## Motivation
The project explores an accessible approach using hardware users may already own. It also investigates whether short per-user calibration improves recognition and user experience compared with generic recognition.

## Proposed approach
Capture hand movements through a webcam, extract landmarks using MediaPipe, recognize five gesture families (point, pinch, swipe, open hand, fist), map gestures to simple desktop actions, and log recognition and task outcomes. The exact action assigned to each gesture will be finalized by the team.

## Research question
Can a camera-based, fine-grained finger-gesture interface provide an effective and usable alternative to conventional mouse interaction for simple desktop tasks?

## Evaluation
The proposed within-subject study compares mouse-only interaction, gesture interaction without calibration, and gesture interaction with calibration. The proposal specifies at least 12 participants. Measures include recognition accuracy, false-positive rate, recognition latency, task completion time, errors/attempts, confusion matrix, SUS and other subjective ratings, and qualitative feedback.

## Research inspiration
Liu, Y., Jiang, F., & Gowda, M. (2020). “Finger Gesture Tracking for Interactive Applications: A Pilot Study with Sign Languages (FinGTrAC).” IMWUT 2020. https://doi.org/10.1145/3414117

AirTouch adapts the broad idea of fine-grained gesture interaction to commodity camera-based sensing. It is inspired by this work, not a reproduction of its wearable sensing system.

## Expected deliverables
- Runnable webcam hand-tracking prototype.
- Recognition for the agreed gesture vocabulary.
- Gesture-to-action mapping and visible feedback.
- Generic and calibrated recognition conditions, to the extent implemented and tested.
- Event logging and analysis scripts.
- Documented study protocol and evaluation results.
