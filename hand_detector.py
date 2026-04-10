"""
hand_detector.py
----------------
Handles MediaPipe hand detection and landmark drawing.
"""

import cv2
import mediapipe as mp
import time

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

class HandDetector:

    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 1,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.8,
        min_tracking_confidence: float = 0.8,
    ):
        self.mp_hands  = mp_hands
        self.mp_draw   = mp_drawing
        self.mp_styles = mp_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode = static_image_mode,
            max_num_hands = max_num_hands,
            model_complexity = model_complexity,
            min_detection_confidence = min_detection_confidence,
            min_tracking_confidence = min_tracking_confidence
        )

        # Store the last detected landmarks (list of 21 dicts: {id, x, y, z})
        self.landmarks: list[dict] = []
        # Raw MediaPipe result for the first hand
        self.hand_landmarks = None
        
        # Stability enhancement: cache last valid detection
        self._last_valid_landmarks: list[dict] = []
        self._last_valid_hand_landmarks = None
        self._last_detection_time: float = 0.0
        self._fallback_duration: float = 0.15  # seconds to retain last detection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_hands(self, frame: "np.ndarray", draw: bool = True) -> "np.ndarray":
        """
        Process a BGR frame, detect hands, optionally draw landmarks.

        Parameters
        ----------
        frame : np.ndarray   BGR image from OpenCV
        draw  : bool         Whether to draw landmarks on the frame

        Returns
        -------
        np.ndarray           The (possibly annotated) frame
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False          # small performance win
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        current_time = time.perf_counter()
        detection_found = False

        if results.multi_hand_landmarks:
            # We only care about the first hand (max_num_hands = 1)
            self.hand_landmarks = results.multi_hand_landmarks[0]
            detection_found = True

            if draw:
                self.mp_draw.draw_landmarks(
                    frame,
                    self.hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )

            # Build a flat list of landmark coordinates (pixel space)
            h, w, _ = frame.shape
            self.landmarks = []
            for idx, lm in enumerate(self.hand_landmarks.landmark):
                self.landmarks.append({
                    "id": idx,
                    "x":  int(lm.x * w),
                    "y":  int(lm.y * h),
                    "z":  lm.z,           # depth (relative)
                })

            # Cache this valid detection
            self._last_valid_landmarks = self.landmarks.copy()
            self._last_valid_hand_landmarks = self.hand_landmarks
            self._last_detection_time = current_time

        else:
            # No detection - check if we can use cached landmarks
            time_since_last = current_time - self._last_detection_time

            if time_since_last <= self._fallback_duration and self._last_valid_landmarks:
                # Use cached landmarks to maintain stability
                self.landmarks = self._last_valid_landmarks
                self.hand_landmarks = self._last_valid_hand_landmarks

                if draw and self.hand_landmarks:
                    self.mp_draw.draw_landmarks(
                        frame,
                        self.hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_styles.get_default_hand_landmarks_style(),
                        self.mp_styles.get_default_hand_connections_style(),
                    )
            else:
                # Fallback expired or no cache - clear detection
                self.landmarks = []
                self.hand_landmarks = None

        return frame

    def get_landmarks(self) -> list[dict]:
        """Return the list of 21 landmark dicts for the detected hand."""
        return self.landmarks

    def hand_detected(self) -> bool:
        """True if at least one hand was found in the last frame."""
        return len(self.landmarks) == 21