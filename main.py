"""
main.py
-------
Entry point for the Hand Finger-Counter desktop application.

Controls
--------
  Q  →  quit
  F  →  toggle fullscreen
  L  →  toggle landmark drawing
"""

import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from hand_detector      import HandDetector
from finger_counter     import FingerCounter
from action_controller  import ActionController


# ── Configuration ─────────────────────────────────────────────────────────────

CAMERA_INDEX        = 0          # 0 = default webcam; change if needed
FRAME_WIDTH         = 1280
FRAME_HEIGHT        = 720
WINDOW_TITLE        = "Hand Finger Counter  |  Q = quit  F = fullscreen  L = landmarks"

# HUD colours  (BGR)
COLOR_GREEN         = (0, 220, 100)
COLOR_WHITE         = (255, 255, 255)
COLOR_BLACK         = (0,   0,   0)
COLOR_AMBER         = (0, 180, 255)
COLOR_DARK_OVERLAY  = (20,  20,  20)
COLOR_CYAN          = (255, 220,  0)
COLOR_YELLOW        = (0,   255, 255)   # bright yellow in BGR for action text

# Action display
ACTION_DISPLAY_DURATION = 2.0    # seconds the action label stays on screen

# Font
FONT                = cv2.FONT_HERSHEY_SIMPLEX

# PIL Font for emoji support
import os

# PIL Font for emoji support (FORCE LOAD)
PIL_FONT = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", 32)

print("[INFO] Loaded font:", PIL_FONT.path if hasattr(PIL_FONT, "path") else "Unknown")


# ── Helpers ───────────────────────────────────────────────────────────────────

def draw_rounded_rect(img, x, y, w, h, radius=12, color=(0, 0, 0), alpha=0.55):
    """Draw a semi-transparent rounded rectangle as a HUD background."""
    overlay = img.copy()
    # Top / bottom straight bars
    cv2.rectangle(overlay, (x + radius, y),            (x + w - radius, y + h),         color, -1)
    # Left / right straight bars
    cv2.rectangle(overlay, (x,          y + radius),   (x + w,          y + h - radius), color, -1)
    # Corners
    for cx, cy in [
        (x + radius,     y + radius),
        (x + w - radius, y + radius),
        (x + radius,     y + h - radius),
        (x + w - radius, y + h - radius),
    ]:
        cv2.circle(overlay, (cx, cy), radius, color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def draw_finger_icons(frame, states: list[bool], ox: int, oy: int):
    """
    Draw 5 small finger indicator circles (filled = up, hollow = down).
    states : [thumb, index, middle, ring, pinky]
    """
    labels  = ["T", "I", "M", "R", "P"]
    spacing = 46
    r       = 18
    for i, (state, label) in enumerate(zip(states, labels)):
        cx = ox + i * spacing
        cy = oy
        if state:
            cv2.circle(frame, (cx, cy), r, COLOR_GREEN, -1)
            cv2.circle(frame, (cx, cy), r, COLOR_WHITE,  2)
        else:
            cv2.circle(frame, (cx, cy), r, COLOR_BLACK, -1)
            cv2.circle(frame, (cx, cy), r, (80, 80, 80), 2)
        cv2.putText(
            frame, label,
            (cx - 7, cy + 6),
            FONT, 0.5, COLOR_WHITE, 1, cv2.LINE_AA,
        )


def draw_action_label(frame, text: str, elapsed: float, duration: float):
    """
    Render the action notification banner centred near the bottom of the frame.

    Uses PIL to support emoji rendering.

    Parameters
    ----------
    frame   : np.ndarray  – current video frame (modified in-place)
    text    : str         – action label to display (with emoji support)
    elapsed : float       – seconds since the action fired
    duration: float       – total seconds the label should be visible
    """
    if elapsed >= duration:
        return  # display window has expired; nothing to draw

    h, w = frame.shape[:2]

    # ── Fade-out in the last 0.5 s ────────────────────────────────────
    fade_window = 0.5
    time_left   = duration - elapsed
    if time_left < fade_window:
        alpha_text = int((time_left / fade_window) * 255)
        alpha_bg   = (time_left / fade_window) * 0.65
    else:
        alpha_text = 255
        alpha_bg   = 0.65

    # ── Convert frame to PIL ──────────────────────────────────────────
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(pil_img, "RGBA")

    # ── Measure text with PIL ─────────────────────────────────────────
    bbox = draw.textbbox((0, 0), text, font=PIL_FONT)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x   = 32
    pad_y   = 20
    card_w  = tw + pad_x * 2
    card_h  = th + pad_y * 2
    card_x  = (w - card_w) // 2
    card_y  = h - card_h - 70

    # ── Draw background on OpenCV frame (with fade) ───────────────────
    draw_rounded_rect(
        frame,
        card_x, card_y, card_w, card_h,
        radius=14,
        color=COLOR_DARK_OVERLAY,
        alpha=alpha_bg,
    )

    # ── Accent top border line ─────────────────────────────────────────
    cv2.line(
        frame,
        (card_x + 14,          card_y),
        (card_x + card_w - 14, card_y),
        COLOR_YELLOW, 2, cv2.LINE_AA,
    )

    # ── Reconvert after background drawing ────────────────────────────
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(pil_img, "RGBA")

    # ── Draw text with PIL (emoji support) ────────────────────────────
    text_x = card_x + pad_x
    text_y = card_y + pad_y

    # Yellow color in RGB with alpha
    text_color = (255, 255, 0, alpha_text)
    draw.text((text_x, text_y), text, font=PIL_FONT, fill=text_color)

    # ── Convert back to OpenCV ────────────────────────────────────────
    frame_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    frame[:] = frame_bgr


def draw_hud(frame, finger_count: int, states: list[bool],
             fps: float, hand_found: bool, draw_landmarks: bool):
    """Overlay all HUD elements onto the frame (in-place)."""

    h, w = frame.shape[:2]

    # ── Top-left card: finger count ───────────────────────────────────
    card_x, card_y, card_w, card_h = 20, 20, 230, 120
    draw_rounded_rect(frame, card_x, card_y, card_w, card_h,
                      radius=14, color=COLOR_DARK_OVERLAY, alpha=0.60)

    label = "Fingers:"
    cv2.putText(frame, label,
                (card_x + 14, card_y + 38),
                FONT, 0.75, COLOR_WHITE, 1, cv2.LINE_AA)

    count_str = str(finger_count) if hand_found else "-"
    cv2.putText(frame, count_str,
                (card_x + 14, card_y + 98),
                FONT, 2.6, COLOR_GREEN if hand_found else COLOR_AMBER,
                4, cv2.LINE_AA)

    # ── Finger icons card ─────────────────────────────────────────────
    icon_card_x, icon_card_y = 20, 160
    icon_card_w, icon_card_h = 262, 60
    draw_rounded_rect(frame, icon_card_x, icon_card_y,
                      icon_card_w, icon_card_h,
                      radius=12, color=COLOR_DARK_OVERLAY, alpha=0.55)
    draw_finger_icons(frame, states,
                      ox=icon_card_x + 30,
                      oy=icon_card_y + 30)

    # ── Status badge (hand / no hand) ─────────────────────────────────
    badge_text  = "HAND DETECTED" if hand_found else "NO HAND"
    badge_color = COLOR_GREEN     if hand_found else COLOR_AMBER
    badge_w     = 200 if hand_found else 140
    bx          = w - badge_w - 20
    by          = 20
    draw_rounded_rect(frame, bx, by, badge_w, 44,
                      radius=10, color=COLOR_DARK_OVERLAY, alpha=0.65)
    cv2.putText(frame, badge_text,
                (bx + 12, by + 30),
                FONT, 0.65, badge_color, 2, cv2.LINE_AA)

    # ── FPS counter ───────────────────────────────────────────────────
    fps_text = f"FPS: {fps:.1f}"
    cv2.putText(frame, fps_text,
                (w - 130, h - 20),
                FONT, 0.6, (160, 160, 160), 1, cv2.LINE_AA)

    # ── Landmarks toggle indicator ─────────────────────────────────────
    lm_text  = "Landmarks: ON" if draw_landmarks else "Landmarks: OFF"
    lm_color = COLOR_GREEN     if draw_landmarks else (100, 100, 100)
    cv2.putText(frame, lm_text,
                (20, h - 20),
                FONT, 0.55, lm_color, 1, cv2.LINE_AA)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    # --- Camera setup ---------------------------------------------------
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {CAMERA_INDEX}.")
        print("        Change CAMERA_INDEX in main.py if you have multiple cameras.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera opened: {actual_w}x{actual_h}")

    # --- Modules --------------------------------------------------------
    detector   = HandDetector(
        max_num_hands            = 1,
        min_detection_confidence = 0.85,
        min_tracking_confidence  = 0.80,
    )
    counter    = FingerCounter()
    controller = ActionController(cooldown=1.5)

    # --- Window ---------------------------------------------------------
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, actual_w, actual_h)

    # --- State ----------------------------------------------------------
    fullscreen           = False
    draw_landmarks       = True
    prev_time            = time.perf_counter()
    finger_count         = 0
    finger_states_       = [False] * 5

    # ── Action display state ──────────────────────────────────────────
    last_action_text:    str   = ""
    action_display_time: float = 0.0   # perf_counter timestamp when action fired

    print("[INFO] Starting — press Q to quit, F for fullscreen, L to toggle landmarks.")

    # ── Main loop ────────────────────────────────────────────────────────
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[WARN] Frame grab failed, retrying...")
            continue

        # Mirror so the display feels like a mirror
        frame = cv2.flip(frame, 1)

        # ── Detection ────────────────────────────────────────────────────
        frame     = detector.find_hands(frame, draw=draw_landmarks)
        landmarks = detector.get_landmarks()

        if detector.hand_detected():
            finger_count   = counter.count(landmarks)
            finger_states_ = counter.finger_states(landmarks)
        else:
            finger_count   = 0
            finger_states_ = [False] * 5

        # ── Action Controller ─────────────────────────────────────────────
        action_label = controller.perform_action(finger_count)

        # ── Update action display state when a new action fires ───────────
        if action_label is not None:
            last_action_text    = action_label
            action_display_time = time.perf_counter()

        # ── FPS ──────────────────────────────────────────────────────────
        now       = time.perf_counter()
        fps       = 1.0 / (now - prev_time + 1e-9)
        prev_time = now

        # ── HUD ──────────────────────────────────────────────────────────
        draw_hud(
            frame,
            finger_count   = finger_count,
            states         = finger_states_,
            fps            = fps,
            hand_found     = detector.hand_detected(),
            draw_landmarks = draw_landmarks,
        )

        # ── Action label overlay ──────────────────────────────────────────
        if last_action_text:
            elapsed = now - action_display_time
            draw_action_label(
                frame,
                text     = last_action_text,
                elapsed  = elapsed,
                duration = ACTION_DISPLAY_DURATION,
            )

        # ── Show ─────────────────────────────────────────────────────────
        cv2.imshow(WINDOW_TITLE, frame)

        # ── Key handling ─────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:          # Q or Esc → quit
            print("[INFO] Quit requested.")
            break

        elif key == ord("f"):                      # F → toggle fullscreen
            fullscreen = not fullscreen
            flag = cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL
            cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, flag)

        elif key == ord("l"):                      # L → toggle landmarks
            draw_landmarks = not draw_landmarks
            state_str = "ON" if draw_landmarks else "OFF"
            print(f"[INFO] Landmarks drawing: {state_str}")

    # ── Clean up ─────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Application closed cleanly.")


if __name__ == "__main__":
    main()