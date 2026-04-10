"""
finger_counter.py
-----------------
Counts the number of raised fingers (0-5) from MediaPipe hand landmarks.

MediaPipe landmark indices used
--------------------------------
Thumb  : 1(CMC) 2(MCP) 3(IP) 4(TIP)
Index  : 5(MCP) 6(PIP) 7(DIP) 8(TIP)
Middle : 9(MCP) 10(PIP) 11(DIP) 12(TIP)
Ring   : 13(MCP) 14(PIP) 15(DIP) 16(TIP)
Pinky  : 17(MCP) 18(PIP) 19(DIP) 20(TIP)

Counting logic
--------------
* Thumb  → compare TIP x vs MCP x (horizontal axis).
           Works for both left and right hands by checking
           which side the thumb tip falls on relative to the
           index-finger MCP.
* Others → TIP y < PIP y  means finger is raised
           (y increases downward, so smaller y = higher on screen).
"""


class FingerCounter:
    """
    Stateless helper that counts raised fingers given a list of
    21 landmark dicts produced by HandDetector.get_landmarks().
    """

    # Tip landmark IDs for each finger
    FINGER_TIPS = [4, 8, 12, 16, 20]

    # The joint just below the tip (PIP for fingers, IP for thumb)
    FINGER_LOWER = [3, 6, 10, 14, 18]

    def count(self, landmarks: list[dict]) -> int:
        """
        Count how many fingers are raised.

        Parameters
        ----------
        landmarks : list[dict]
            21 landmark dicts with keys 'id', 'x', 'y', 'z'.
            Must contain exactly 21 entries (i.e., a hand was detected).

        Returns
        -------
        int  Number of fingers raised (0–5), or 0 if no hand data.
        """
        if len(landmarks) != 21:
            return 0

        fingers_up = 0

        # ── Thumb ─────────────────────────────────────────────────────
        # We determine hand orientation by comparing the wrist (0) to
        # the pinky MCP (17).  If wrist.x < pinky.x the hand is facing
        # right (typical front-facing right hand); otherwise it is
        # facing left (or is a left hand / mirrored feed).
        #
        # For a right-facing hand: thumb is up when tip.x < MCP.x
        # For a left-facing  hand: thumb is up when tip.x > MCP.x
        wrist_x      = landmarks[0]["x"]
        pinky_mcp_x  = landmarks[17]["x"]
        thumb_tip_x  = landmarks[self.FINGER_TIPS[0]]["x"]
        thumb_mcp_x  = landmarks[2]["x"]          # thumb MCP

        if wrist_x < pinky_mcp_x:
            # Hand oriented to the right → thumb raises to the left
            if thumb_tip_x < thumb_mcp_x:
                fingers_up += 1
        else:
            # Hand oriented to the left → thumb raises to the right
            if thumb_tip_x > thumb_mcp_x:
                fingers_up += 1

        # ── Four Fingers ──────────────────────────────────────────────
        for tip_id, lower_id in zip(
            self.FINGER_TIPS[1:], self.FINGER_LOWER[1:]
        ):
            tip_y   = landmarks[tip_id]["y"]
            lower_y = landmarks[lower_id]["y"]

            # Tip is above the PIP joint → finger is raised
            if tip_y < lower_y:
                fingers_up += 1

        return fingers_up

    def finger_states(self, landmarks: list[dict]) -> list[bool]:
        """
        Return a per-finger boolean list [thumb, index, middle, ring, pinky].
        True = raised, False = folded.
        Useful for future gesture-recognition extensions.
        """
        if len(landmarks) != 21:
            return [False] * 5

        states: list[bool] = []

        # Thumb
        wrist_x     = landmarks[0]["x"]
        pinky_mcp_x = landmarks[17]["x"]
        thumb_tip_x = landmarks[self.FINGER_TIPS[0]]["x"]
        thumb_mcp_x = landmarks[2]["x"]

        if wrist_x < pinky_mcp_x:
            states.append(thumb_tip_x < thumb_mcp_x)
        else:
            states.append(thumb_tip_x > thumb_mcp_x)

        # Other fingers
        for tip_id, lower_id in zip(
            self.FINGER_TIPS[1:], self.FINGER_LOWER[1:]
        ):
            states.append(landmarks[tip_id]["y"] < landmarks[lower_id]["y"])

        return states
