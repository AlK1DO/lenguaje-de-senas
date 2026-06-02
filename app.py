import cv2
import json
import base64
import numpy as np
import time
from flask import Flask, render_template, jsonify, request
from sign_detector import SignDetector

app = Flask(__name__)

# ── Detector global ───────────────────────────────────────────────────────────
detector = SignDetector()

# ── Estado de historial ───────────────────────────────────────────────────────
history = []
MAX_HISTORY = 20


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    """
    Recibe un frame en base64 desde el navegador (capturado con getUserMedia),
    lo procesa con MediaPipe y devuelve la letra detectada + frame anotado.
    """
    global history

    data = request.get_json(silent=True)
    if not data or "frame" not in data:
        return jsonify({"error": "No frame provided"}), 400

    # Decodificar base64 → numpy array
    try:
        img_data = data["frame"]
        # Remover prefijo "data:image/jpeg;base64," si viene incluido
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]

        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid frame"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Procesar con MediaPipe
    annotated, signs = detector.process_frame(frame)

    # Actualizar historial
    if signs:
        combined = " + ".join(signs)
        if not history or history[-1] != combined:
            history.append(combined)
            if len(history) > MAX_HISTORY:
                history.pop(0)

    # Codificar frame anotado en base64 para devolverlo
    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    return jsonify({
        "signs": signs,
        "history": history[-10:],
        "annotated_frame": annotated_b64,
    })


@app.route("/api/clear_history", methods=["POST", "GET"])
def clear_history():
    global history
    history = []
    return jsonify({"status": "cleared"})


@app.route("/api/status")
def status():
    return jsonify({
        "signs": [],
        "history": history[-10:],
    })


@app.route("/api/signs")
def get_signs_info():
    signs = [
        {"letter": "A",    "description": "Puño cerrado, pulgar al lado del índice",       "static": True},
        {"letter": "B",    "description": "4 dedos arriba juntos, pulgar doblado",          "static": True},
        {"letter": "C",    "description": "Mano curvada en forma de C",                     "static": True},
        {"letter": "D",    "description": "Índice arriba, pulgar toca el dedo medio",       "static": True},
        {"letter": "E",    "description": "Todos los dedos doblados hacia la palma",        "static": True},
        {"letter": "F",    "description": "Índice y pulgar se tocan, otros 3 arriba",       "static": True},
        {"letter": "G",    "description": "Índice y pulgar apuntan horizontalmente",        "static": True},
        {"letter": "H",    "description": "Índice y medio extendidos horizontalmente",      "static": True},
        {"letter": "I",    "description": "Solo el meñique arriba",                         "static": True},
        {"letter": "J",    "description": "Requiere movimiento (trazo J)",                  "static": False},
        {"letter": "K",    "description": "Índice y medio arriba, pulgar entre ellos",      "static": True},
        {"letter": "L",    "description": "Índice arriba y pulgar extendido (forma L)",     "static": True},
        {"letter": "M",    "description": "3 dedos doblados sobre el pulgar",               "static": True},
        {"letter": "N",    "description": "2 dedos doblados sobre el pulgar",               "static": True},
        {"letter": "O",    "description": "Todos los dedos curvados tocando el pulgar",     "static": True},
        {"letter": "P",    "description": "Como K pero con la mano apuntando hacia abajo",  "static": True},
        {"letter": "Q",    "description": "Como G pero apuntando hacia abajo",              "static": True},
        {"letter": "R",    "description": "Índice y medio cruzados",                        "static": True},
        {"letter": "S",    "description": "Puño cerrado con pulgar sobre los dedos",        "static": True},
        {"letter": "T",    "description": "Pulgar entre índice y medio (puño)",             "static": True},
        {"letter": "U",    "description": "Índice y medio arriba juntos y paralelos",       "static": True},
        {"letter": "V",    "description": "Índice y medio arriba separados (paz)",          "static": True},
        {"letter": "W",    "description": "Índice, medio y anular arriba",                  "static": True},
        {"letter": "X",    "description": "Índice doblado en gancho",                       "static": True},
        {"letter": "Y",    "description": "Pulgar y meñique extendidos",                    "static": True},
        {"letter": "Z",    "description": "Requiere movimiento (trazo Z)",                  "static": False},
        {"letter": "5",    "description": "Mano completamente abierta",                     "static": True},
        {"letter": "Rock", "description": "Índice y meñique arriba",                        "static": True},
        {"letter": "Pulgar","description": "Pulgar arriba",                                 "static": True},
        {"letter": "Puno", "description": "Puño cerrado",                                   "static": True},
    ]
    return jsonify(signs)


if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))
    print(f"Detector de Señas -> http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
