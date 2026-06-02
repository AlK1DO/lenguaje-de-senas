import cv2
import mediapipe as mp
import numpy as np
from math import degrees, acos

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


# ── Lógica de ángulos (Proyecto_señas) ───────────────────────────────────────

def _angle_from_points(p1, p2, p3):
    """Calcula el ángulo en p2 formado por p1-p2-p3 usando la ley del coseno."""
    l1 = np.linalg.norm(p2 - p3)
    l2 = np.linalg.norm(p1 - p3)
    l3 = np.linalg.norm(p1 - p2)
    denom = 2 * l1 * l3
    if denom == 0:
        return 0
    num_den = (l1**2 + l3**2 - l2**2) / denom
    if not (-1 < num_den < 1):
        return 0
    return round(degrees(abs(acos(num_den))))


def obtener_angulos(hand_landmarks, width, height):
    """
    Devuelve [angulosid, pinky] donde:
      angulosid = [meñique, anular, medio, índice, pulgar_ext, pulgar_int]
      pinky     = [x, y] del tip del meñique en píxeles
    """
    lm = hand_landmarks.landmark

    def px(idx):
        return np.array([
            int(lm[idx].x * width),
            int(lm[idx].y * height)
        ])

    # Meñique: TIP=20, PIP=18, MCP=17
    a1 = _angle_from_points(px(20), px(18), px(17))
    # Anular: TIP=16, PIP=14, MCP=13
    a2 = _angle_from_points(px(16), px(14), px(13))
    # Medio: TIP=12, PIP=10, MCP=9
    a3 = _angle_from_points(px(12), px(10), px(9))
    # Índice: TIP=8, PIP=6, MCP=5
    a4 = _angle_from_points(px(8), px(6), px(5))
    # Pulgar externo: TIP=4, IP=3, MCP=2
    a5 = _angle_from_points(px(4), px(3), px(2))
    # Pulgar interno: TIP=4, MCP=2, WRIST=0
    a6 = _angle_from_points(px(4), px(2), px(0))

    angulosid = [a1, a2, a3, a4, a5, a6]
    pinky = [int(lm[20].x * width), int(lm[20].y * height)]
    return [angulosid, pinky]


def dedos_desde_angulos(angulosid):
    """
    Convierte ángulos a lista de dedos extendidos [pulgar_ext, pulgar_int, meñique, anular, medio, índice].
    Retorna lista de 6 bits (0/1).
    """
    dedos = []
    # pulgar externo
    dedos.append(1 if angulosid[5] > 125 else 0)
    # pulgar interno
    dedos.append(1 if angulosid[4] > 150 else 0)
    # 4 dedos: meñique, anular, medio, índice
    for i in range(4):
        dedos.append(1 if angulosid[i] > 90 else 0)
    return dedos


def clasificar_por_angulos(dedos):
    """
    Clasifica la seña usando la lógica de condicionales del Proyecto_señas.
    Retorna la letra detectada o None.
    """
    # Vocales
    if dedos == [1, 1, 0, 0, 0, 0]: return "A"
    if dedos == [0, 0, 0, 0, 0, 0]: return "E"
    if dedos == [0, 0, 1, 0, 0, 0]: return "I"
    if dedos == [1, 0, 1, 0, 0, 0]: return "O"
    if dedos == [0, 0, 1, 0, 0, 1]: return "U"
    # Consonantes
    if dedos == [0, 0, 1, 1, 1, 1]: return "B"
    if dedos == [0, 0, 0, 0, 0, 1]: return "D"
    if dedos == [1, 1, 0, 0, 1, 1]: return "K"
    if dedos == [1, 1, 0, 0, 0, 1]: return "L"
    if dedos == [0, 1, 0, 1, 1, 1]: return "W"
    if dedos == [0, 1, 0, 0, 1, 1]: return "N"
    if dedos == [1, 1, 1, 0, 0, 0]: return "Y"
    if dedos == [1, 1, 1, 1, 1, 0]: return "F"
    if dedos == [0, 1, 1, 1, 1, 1]: return "P"
    if dedos == [0, 1, 0, 0, 1, 1]: return "V"
    return None


# ── Helpers de geometría (enfoque landmarks) ──────────────────────────────────

def d(lm, a, b):
    return np.sqrt((lm[a].x - lm[b].x)**2 + (lm[a].y - lm[b].y)**2)


def finger_extended(lm, tip, dip, pip, mcp):
    return lm[tip].y < lm[pip].y - 0.025


def finger_curled(lm, tip, pip):
    return lm[tip].y >= lm[pip].y - 0.01


def finger_half_bent(lm, tip, pip, mcp):
    return lm[mcp].y > lm[tip].y > lm[pip].y


def thumb_extended(lm, is_right):
    if is_right:
        return lm[4].x < lm[3].x - 0.015
    else:
        return lm[4].x > lm[3].x + 0.015


def touching(lm, a, b, threshold=0.055):
    return d(lm, a, b) < threshold


# ── Clasificador principal (landmarks + ángulos combinados) ───────────────────

def classify_sign(hand_landmarks, handedness, width=640, height=480):
    lm = hand_landmarks.landmark
    is_right = handedness.classification[0].label == "Right"

    # ── Intentar primero con lógica de ángulos ────────────────────────────────
    try:
        angulos_data = obtener_angulos(hand_landmarks, width, height)
        angulosid = angulos_data[0]
        pinky_coords = angulos_data[1]
        dedos = dedos_desde_angulos(angulosid)
        resultado_angulos = clasificar_por_angulos(dedos)
        if resultado_angulos:
            return resultado_angulos, pinky_coords, dedos
    except Exception:
        pinky_coords = [0, 0]
        dedos = [0] * 6

    # ── Fallback: clasificación por landmarks normalizados ────────────────────
    IDX  = finger_extended(lm, 8,  7,  6,  5)
    MID  = finger_extended(lm, 12, 11, 10, 9)
    RNG  = finger_extended(lm, 16, 15, 14, 13)
    PNK  = finger_extended(lm, 20, 19, 18, 17)
    THB  = thumb_extended(lm, is_right)

    IDX_curl = finger_curled(lm, 8,  6)
    MID_curl = finger_curled(lm, 12, 10)
    RNG_curl = finger_curled(lm, 16, 14)
    PNK_curl = finger_curled(lm, 20, 18)

    d_ti = d(lm, 4, 8)
    d_tm = d(lm, 4, 12)
    d_tr = d(lm, 4, 16)
    d_tp = d(lm, 4, 20)
    d_im = d(lm, 8, 12)

    wrist_y = lm[0].y
    sign = "?"

    if IDX_curl and MID_curl and RNG_curl and PNK_curl and THB:
        if lm[4].y < lm[8].y - 0.01:
            sign = "A"
    elif IDX and MID and RNG and PNK and not THB and d_im < 0.08:
        sign = "B"
    elif not IDX and not MID and not RNG and not PNK and not THB and touching(lm, 4, 8, 0.07):
        sign = "O"
    elif not IDX and not MID and not RNG and PNK and not THB:
        sign = "I"
    elif IDX and not MID and not RNG and not PNK and THB:
        idx_vert  = abs(lm[8].y - lm[5].y)
        thb_horiz = abs(lm[4].x - lm[2].x)
        if idx_vert > 0.08 and thb_horiz > 0.05:
            sign = "L"
        elif lm[8].y > wrist_y:
            sign = "Q"
        else:
            sign = "G"
    elif IDX and MID and not RNG and not PNK and not THB:
        if d_im < 0.035:
            sign = "R"
        elif d_im < 0.05:
            sign = "U"
        else:
            sign = "V"
    elif IDX and MID and not RNG and not PNK and THB:
        if touching(lm, 4, 12, 0.10):
            sign = "K"
        elif lm[8].y > wrist_y:
            sign = "P"
    elif IDX and MID and RNG and not PNK and not THB:
        sign = "W"
    elif not IDX and MID and RNG and PNK and touching(lm, 4, 8, 0.06):
        sign = "F"
    elif IDX_curl and MID_curl and RNG_curl and PNK_curl and not THB:
        if d_ti < 0.10 and d_tm < 0.10 and d_tr > 0.10:
            sign = "N"
        elif d_ti < 0.12 and d_tm < 0.12 and d_tr < 0.12 and d_tp > 0.10:
            sign = "M"
        elif lm[8].y > lm[6].y - 0.02:
            sign = "E"
        else:
            sign = "S"
    elif IDX_curl and MID_curl and RNG_curl and PNK_curl and THB:
        if d(lm, 4, 5) < 0.07:
            sign = "T"
    elif IDX and not MID and not RNG and PNK and not THB:
        sign = "Rock 🤘"
    elif THB and not IDX and not MID and not RNG and PNK:
        sign = "Y"
    elif THB and IDX and MID and RNG and PNK:
        sign = "5 ✋"
    elif THB and not IDX and not MID and not RNG and not PNK:
        sign = "👍"
    elif not THB and not IDX and not MID and not RNG and not PNK:
        sign = "✊"

    return sign, pinky_coords, dedos


# ── Detector class ────────────────────────────────────────────────────────────

class SignDetector:
    def __init__(self):
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.75,
            min_tracking_confidence=0.65,
        )
        self.current_signs = []
        self.sign_history  = []
        self.max_history   = 20
        # Para detección de movimiento (letra J)
        self._prev_pinky   = {}   # hand_index -> last pinky coords sum
        self._motion_sign  = {}   # hand_index -> sign if motion detected

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results  = self.hands.process(rgb)

        signs    = []
        annotated = frame.copy()

        if results.multi_hand_landmarks:
            for idx, (hand_lm, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                mp_drawing.draw_landmarks(
                    annotated, hand_lm,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style(),
                )

                sign, pinky_coords, dedos = classify_sign(hand_lm, handedness, w, h)

                # ── Detección de movimiento para J ────────────────────────────
                pinky_sum = pinky_coords[0] + pinky_coords[1]
                prev_sum  = self._prev_pinky.get(idx, pinky_sum)
                delta     = abs(pinky_sum - prev_sum)
                self._prev_pinky[idx] = pinky_sum

                if dedos == [0, 0, 1, 0, 0, 0] and delta > 30:
                    sign = "J"

                signs.append(sign)

                # ── Bounding box ──────────────────────────────────────────────
                xs = [lm.x * w for lm in hand_lm.landmark]
                ys = [lm.y * h for lm in hand_lm.landmark]
                x1 = max(0, int(min(xs)) - 20)
                y1 = max(0, int(min(ys)) - 20)
                x2 = min(w, int(max(xs)) + 20)
                y2 = min(h, int(max(ys)) + 20)

                # Color según si es movimiento o estático
                color = (255, 140, 0) if sign == "J" else (99, 102, 241)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

                label = sign
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
                cv2.rectangle(annotated, (x1, y1 - lh - 14), (x1 + lw + 12, y1), color, -1)
                cv2.putText(
                    annotated, label,
                    (x1 + 6, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                    (255, 255, 255), 2,
                )

        self.current_signs = signs

        if signs:
            combined = " + ".join(signs)
            if not self.sign_history or self.sign_history[-1] != combined:
                self.sign_history.append(combined)
                if len(self.sign_history) > self.max_history:
                    self.sign_history.pop(0)

        return annotated, signs

    def release(self):
        self.hands.close()
