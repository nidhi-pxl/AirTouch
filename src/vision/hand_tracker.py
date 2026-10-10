"""
Hand Tracking Module
Provides a reusable HandTracker class utilizing MediaPipe Hands for detection.
Separates core vision tracking logic from visuals, enabling flexible reuse.
"""

import math
import cv2
import numpy as np
import mediapipe as mp


class HandTracker:
    """
    A class to detect hands, extract landmark positions, and draw overlays
    using MediaPipe Hands.
    """

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        """
        Initializes the MediaPipe Hands configuration.

        Args:
            max_num_hands: Maximum number of hands to detect.
            min_detection_confidence: Minimum confidence value for hand detection.
            min_tracking_confidence: Minimum confidence value for tracking landmarks.
        """
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        # Initialize MediaPipe Hands solutions
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_num_hands,
            model_complexity=1,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

    def process_frame(self, img: np.ndarray) -> None:
        """
        Processes a BGR image frame through the MediaPipe Hands model.

        Args:
            img: The input BGR image from OpenCV.
        """
        # MediaPipe requires RGB images
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

    def get_hands_info(self, img: np.ndarray) -> list[dict]:
        """
        Extracts structured data for all detected hands from the last processed frame.

        Args:
            img: The input BGR image (used to scale landmarks to pixel coordinates).

        Returns:
            A list of dicts. Each dict represents a hand with keys:
            - "lm_list": List of [x, y, z] coordinates for the 21 landmarks.
            - "bbox": (xmin, ymin, width, height) of the hand.
            - "center": (cx, cy) center coordinate of the bounding box.
            - "type": "Left" or "Right" handedness.
            - "score": Confidence score of the detection.
        """
        hands_info = []
        if not self.results or not self.results.multi_hand_landmarks:
            return hands_info

        h, w, _ = img.shape

        for hand_idx, hand_lms in enumerate(self.results.multi_hand_landmarks):
            lm_list = []
            x_list = []
            y_list = []

            for lm in hand_lms.landmark:
                # Convert normalized coordinates (0.0 - 1.0) to pixel values
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([cx, cy, lm.z])
                x_list.append(cx)
                y_list.append(cy)

            # Compute bounding box coordinates
            xmin, xmax = min(x_list), max(x_list)
            ymin, ymax = min(y_list), max(y_list)
            bbox_w, bbox_h = xmax - xmin, ymax - ymin
            bbox = (xmin, ymin, bbox_w, bbox_h)
            center = (xmin + bbox_w // 2, ymin + bbox_h // 2)

            # Extract handedness and confidence score
            handedness_label = "Unknown"
            score = 0.0
            if self.results.multi_handedness:
                hand_class = self.results.multi_handedness[hand_idx]
                handedness_label = hand_class.classification[0].label
                score = hand_class.classification[0].score

            hands_info.append({
                "lm_list": lm_list,
                "bbox": bbox,
                "center": center,
                "type": handedness_label,
                "score": score,
            })

        return hands_info

    def draw_landmarks(self, img: np.ndarray) -> np.ndarray:
        """
        Draws standard MediaPipe landmarks and connection lines on the provided image.

        Args:
            img: BGR image to draw upon.

        Returns:
            The image with overlays drawn.
        """
        if self.results and self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    img, hand_lms, self.mp_hands.HAND_CONNECTIONS
                )
        return img

    def get_finger_states(self, hand_info: dict) -> list[int]:
        """
        Determines the open/closed state of each of the 5 fingers.
        Uses a rotation-invariant geometric approach.

        Args:
            hand_info: The dictionary returned by get_hands_info for a single hand.

        Returns:
            List of 5 integers (0 for closed, 1 for open) matching:
            [Thumb, Index, Middle, Ring, Pinky]
        """
        lm_list = hand_info["lm_list"]
        fingers = []

        # Helper function to compute Euclidean distance
        def get_dist(p1, p2):
            return math.hypot(lm_list[p2][0] - lm_list[p1][0], lm_list[p2][1] - lm_list[p1][1])

        # Hand scale represented by the distance from wrist (0) to middle MCP joint (9)
        hand_scale = get_dist(0, 9)
        if hand_scale == 0:
            hand_scale = 1.0  # Prevent division by zero

        # 1. Thumb State:
        # Distance from thumb tip (4) to index finger MCP (5), normalized by hand scale.
        # If the thumb is extended, this distance is large.
        thumb_dist = get_dist(4, 5) / hand_scale
        # Typically, thumb_dist > 0.45 means the thumb is open
        fingers.append(1 if thumb_dist > 0.45 else 0)

        # 2. Other 4 fingers:
        # Compare distance from tip to wrist (0) vs. PIP joint to wrist.
        # Index (8 vs 6), Middle (12 vs 10), Ring (16 vs 14), Pinky (20 vs 18)
        tip_ids = [8, 12, 16, 20]
        pip_ids = [6, 10, 14, 18]

        for tip, pip in zip(tip_ids, pip_ids):
            tip_dist = get_dist(tip, 0)
            pip_dist = get_dist(pip, 0)
            fingers.append(1 if tip_dist > pip_dist else 0)

        return fingers

    def find_distance(
        self,
        p1: int,
        p2: int,
        lm_list: list,
        img: np.ndarray = None,
        draw: bool = True,
        r: int = 8,
        t: int = 2,
    ) -> tuple[float, list, np.ndarray | None]:
        """
        Calculates pixel distance between two landmarks.

        Args:
            p1: Landmark ID of first point.
            p2: Landmark ID of second point.
            lm_list: The landmark list of the hand.
            img: Optional BGR image to draw a line and endpoints on.
            draw: True to draw on the image.
            r: Radius of marker circles.
            t: Thickness of line.

        Returns:
            A tuple of (distance, list[x1, y1, x2, y2, cx, cy], img).
        """
        x1, y1 = lm_list[p1][0], lm_list[p1][1]
        x2, y2 = lm_list[p2][0], lm_list[p2][1]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        distance = math.hypot(x2 - x1, y2 - y1)

        if img is not None and draw:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), t)
            cv2.circle(img, (x1, y1), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), r, (0, 0, 255), cv2.FILLED)

        return distance, [x1, y1, x2, y2, cx, cy], img
