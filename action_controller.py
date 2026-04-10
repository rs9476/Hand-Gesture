"""
action_controller.py
--------------------
Maps finger counts to system actions and executes them via PyAutoGUI.

Action Mapping
--------------
  1 finger  → Open YouTube
  2 fingers → Volume Up
  3 fingers → Volume Down
  4 fingers → Mute / Unmute
  5 fingers → Lock Screen (prints message + hotkey)

Stability
---------
  * A gesture must be held for HOLD_TIME seconds before triggering.
  * If the gesture changes before HOLD_TIME → timer resets.
  * Actions only fire after stable detection.
  * A per-action cooldown (default 1.5 s) prevents repeated triggering.
"""

import time
import pyautogui
import webbrowser

# Disable PyAutoGUI's fail-safe pause to keep the loop responsive
pyautogui.PAUSE = 0.0


class ActionController:
    """
    Translates a finger count into a system-level action.

    Parameters
    ----------
    cooldown : float
        Minimum seconds that must elapse between consecutive action
        executions (even when the finger count stays the same).
    hold_time : float
        Minimum seconds a gesture must be held before it is confirmed
        and its mapped action is executed.
    """

    # Sentinel value meaning "no gesture is being tracked"
    _NO_GESTURE: int = -1

    def __init__(self, cooldown: float = 1.5, hold_time: float = 1.5):
        self._cooldown   = cooldown
        self._hold_time  = hold_time

        # ── Cooldown tracking ─────────────────────────────────────────
        self._last_confirmed_count: int   = self._NO_GESTURE
        self._last_action_ts:       float = 0.0

        # ── Stability / hold tracking ─────────────────────────────────
        self._candidate_count:      int   = self._NO_GESTURE
        self._candidate_start_ts:   float = 0.0

        # ── Mute state tracking ───────────────────────────────────────
        self._is_muted: bool = False

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def perform_action(self, finger_count: int) -> str | None:
        """
        Evaluate *finger_count* through the stability layer and fire the
        mapped action only after the gesture has been held long enough.

        Stability Rules
        ---------------
        1. A new / different finger count starts (or resets) the hold timer.
        2. The gesture must remain unchanged for ``hold_time`` seconds.
        3. Once confirmed, the action fires only if ``cooldown`` seconds
           have elapsed since the last executed action.
        4. A confirmed gesture is not re-triggered until the finger count
           changes and a new hold cycle completes.

        Parameters
        ----------
        finger_count : int
            Number of raised fingers reported by FingerCounter (0–5).

        Returns
        -------
        str | None
            Descriptive action label if an action was executed this frame,
            or ``None`` if no action fired.
        """
        now = time.perf_counter()

        # ── Step 1: Stability gate ────────────────────────────────────
        if finger_count != self._candidate_count:
            # Gesture changed → restart hold timer with new candidate
            self._candidate_count    = finger_count
            self._candidate_start_ts = now
            return None  # not stable yet; do nothing this frame

        # Gesture is the same as the candidate – check hold duration
        hold_elapsed = now - self._candidate_start_ts
        if hold_elapsed < self._hold_time:
            return None  # still within the required hold window

        # ── Step 2: Avoid re-triggering the same confirmed gesture ────
        if finger_count == self._last_confirmed_count:
            return None  # already acted on this stable gesture

        # ── Step 3: Respect cooldown between actions ──────────────────
        if now - self._last_action_ts < self._cooldown:
            return None

        # ── Step 4: Confirm gesture and dispatch action ───────────────
        self._last_confirmed_count = finger_count
        self._last_action_ts       = now

        action = self._ACTION_MAP.get(finger_count)
        if action is not None:
            label = action(self)
            return label

        return None

    # ------------------------------------------------------------------ #
    #  Private action implementations                                      #
    # ------------------------------------------------------------------ #

    def _action_open_youtube(self) -> str:
        """1 finger → Open YouTube."""
        print("[ACTION] Opening YouTube")
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube🌐"

    def _action_volume_up(self) -> str:
        """2 fingers → Volume Up."""
        print("[ACTION] Volume Up")
        pyautogui.press("volumeup")
        return "Action: Volume Up🔊"

    def _action_volume_down(self) -> str:
        """3 fingers → Volume Down."""
        print("[ACTION] Volume Down")
        pyautogui.press("volumedown")
        return "Action: Volume Down🔉"

    def _action_mute_toggle(self) -> str:
        """4 fingers → Mute / Unmute (toggles internal mute state)."""
        pyautogui.press("volumemute")
        if not self._is_muted:
            self._is_muted = True
            print("[ACTION] Muted")
            return "Action: Muted🔇"
        else:
            self._is_muted = False
            print("[ACTION] Unmuted")
            return "Action: Unmuted🔊"

    def _action_lock_screen(self) -> str:
        """5 fingers → Lock Screen."""
        print("[ACTION] Lock Screen")
        # Windows: Win + L
        pyautogui.hotkey("win", "l")
        return "Action: Lock Screen🔒"

    # ── Finger-count → method mapping ────────────────────────────────
    _ACTION_MAP: dict = {
        1: _action_open_youtube,
        2: _action_volume_up,
        3: _action_volume_down,
        4: _action_mute_toggle,
        5: _action_lock_screen,
    }