# 🤟 Detector de Lenguaje de Señas

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-0097A7?style=for-the-badge&logo=google&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.10-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-22.0-499848?style=for-the-badge&logo=gunicorn&logoColor=white)

<br/>

> Aplicación web que detecta en tiempo real letras del abecedario en lenguaje de señas usando la cámara del navegador y visión por computadora.

</div>

---

## 📌 ¿Qué es?

Es una app web donde el usuario abre el navegador, activa la cámara y el sistema detecta automáticamente qué letra del abecedario está haciendo con la mano. La detección ocurre en tiempo real, frame por frame, sin necesidad de instalar ningún software adicional.

El proyecto combina dos tecnologías clave:
- **MediaPipe** (Google) para detectar los puntos de la mano
- **Geometría de ángulos** para interpretar la posición de los dedos

---

## 🎯 ¿Para qué sirve?

- Aprender y practicar el abecedario en lenguaje de señas
- Recibir retroalimentación visual inmediata al hacer una seña
- Construir palabras letra por letra usando solo la mano
- Demostración práctica de visión por computadora aplicada a la inclusión

---

## 📁 Estructura del proyecto

```
señas/
│
├── app.py               → Servidor Flask: recibe frames, llama al detector, devuelve resultados
├── sign_detector.py     → Motor de detección: MediaPipe + ángulos + fallback por landmarks
├── requirements.txt     → Dependencias de Python
├── Procfile             → Instrucción de arranque para Railway (producción)
├── runtime.txt          → Versión de Python que usa el servidor en la nube
│
├── templates/
│   └── index.html       → Toda la interfaz: detector, abecedario, sección de info
│
└── static/
    ├── css/
    │   └── style.css    → Diseño visual completo (paleta azul marino + dorado)
    └── js/
        └── app.js       → Captura de cámara, envío de frames, actualización de UI
```

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Versión | Rol en el proyecto |
|---|---|---|
| **Python** | 3.11 | Lenguaje principal del backend |
| **Flask** | 3.0 | Servidor web que expone la API REST |
| **MediaPipe** | 0.10 | Detecta los 21 landmarks de la mano en cada frame |
| **OpenCV Headless** | 4.10 | Decodifica imágenes y dibuja anotaciones sobre los frames |
| **NumPy** | 1.26 | Operaciones vectoriales para el cálculo de ángulos |
| **Gunicorn** | 22.0 | Servidor WSGI para correr en producción (Railway) |
| **HTML / CSS / JS** | — | Frontend nativo, sin frameworks |

> **¿Por qué `opencv-python-headless`?** La versión estándar de OpenCV requiere librerías gráficas del sistema (Qt, GTK) para mostrar ventanas. En un servidor en la nube esas librerías no existen, así que se usa la versión `headless` que solo procesa imágenes sin necesidad de pantalla.

---

## ⚙️ Cómo funciona — flujo completo

```
[Cámara del usuario]
       ↓
[Navegador captura frame con getUserMedia]
       ↓
[Frame → JPEG → base64 → POST /api/process_frame]
       ↓
[Servidor Flask recibe el frame]
       ↓
[OpenCV decodifica la imagen]
       ↓
[MediaPipe detecta 21 landmarks de la mano]
       ↓
[Se calculan ángulos por dedo → array de 6 bits]
       ↓
[Comparación con reglas del abecedario → letra]
       ↓
[OpenCV anota el frame con bounding box + letra]
       ↓
[Frame anotado → base64 → JSON de respuesta]
       ↓
[Navegador muestra el frame y la letra detectada]
```

---

## 🔬 Detección en detalle

### Los 21 landmarks de MediaPipe

MediaPipe analiza cada frame e identifica 21 puntos clave de la mano, cada uno con coordenadas `x`, `y` normalizadas entre 0 y 1:

```
         8   12  16  20        ← puntas de los dedos (TIP)
         |   |   |   |
         7   11  15  19        ← articulación distal (DIP)
         |   |   |   |
     4   6   10  14  18        ← articulación media (PIP)
     |   5   9   13  17        ← base del dedo (MCP)
     3   |
     |   0  ← muñeca (WRIST)
     2
     |
     1
```

Cada dedo usa 4 puntos: TIP, DIP, PIP y MCP. El pulgar tiene su propia lógica porque se mueve en otro eje.

---

### Cálculo de ángulos (método principal)

Para cada dedo se toman 3 puntos: la punta (TIP), la articulación media (PIP) y la base (MCP). Con esos 3 puntos se calcula el **ángulo en la articulación** usando la **ley del coseno**:

```python
def _angle_from_points(p1, p2, p3):
    l1 = np.linalg.norm(p2 - p3)   # distancia p2-p3
    l2 = np.linalg.norm(p1 - p3)   # distancia p1-p3
    l3 = np.linalg.norm(p1 - p2)   # distancia p1-p2

    num_den = (l1**2 + l3**2 - l2**2) / (2 * l1 * l3)
    return round(degrees(abs(acos(num_den))))
```

El resultado es un ángulo en grados. La regla es simple:

| Ángulo | Estado del dedo |
|---|---|
| **> 90°** | Extendido → `1` |
| **≤ 90°** | Doblado → `0` |

Esto se aplica a los 6 "dedos" (contando el pulgar doble) y genera el array de detección:

```python
dedos = [pulgar_ext, pulgar_int, meñique, anular, medio, índice]
#         0 o 1       0 o 1      0 o 1    0 o 1   0 o 1   0 o 1
```

---

### Clasificación por patrones

El array de 6 bits se compara directamente contra los patrones de cada letra:

```python
def clasificar_por_angulos(dedos):
    # Vocales
    if dedos == [1, 1, 0, 0, 0, 0]: return "A"   # puño + pulgar al lado
    if dedos == [0, 0, 0, 0, 0, 0]: return "E"   # todos los dedos doblados
    if dedos == [0, 0, 1, 0, 0, 0]: return "I"   # solo meñique arriba
    if dedos == [1, 0, 1, 0, 0, 0]: return "O"   # pulgar + meñique
    if dedos == [0, 0, 1, 0, 0, 1]: return "U"   # meñique + índice

    # Consonantes
    if dedos == [0, 0, 1, 1, 1, 1]: return "B"   # 4 dedos arriba
    if dedos == [0, 0, 0, 0, 0, 1]: return "D"   # solo índice
    if dedos == [1, 1, 0, 0, 1, 1]: return "K"   # índice + medio + pulgar
    if dedos == [1, 1, 0, 0, 0, 1]: return "L"   # índice + pulgar (forma L)
    if dedos == [1, 1, 1, 0, 0, 0]: return "Y"   # pulgar + meñique
    # ... y más letras
```

---

### Método fallback (landmarks normalizados)

Si el método de ángulos no encuentra match, se activa un segundo método que evalúa **distancias y posiciones relativas** entre landmarks. Este método cubre letras más complejas como C, G, H, R, S, T, X:

```python
def finger_extended(lm, tip, dip, pip, mcp):
    # El dedo está extendido si la punta está claramente por encima del PIP
    return lm[tip].y < lm[pip].y - 0.025

def touching(lm, a, b, threshold=0.055):
    # Dos landmarks se "tocan" si están suficientemente cerca
    return d(lm, a, b) < threshold

# Ejemplo: letra F = índice+pulgar se tocan, los otros 3 extendidos
if not IDX and MID and RNG and PNK:
    if touching(lm, 4, 8, 0.06):
        return "F"
```

---

### Detección de movimiento — letra J

La J no es una postura estática, requiere trazar una J en el aire con el meñique. Se detecta comparando la posición del meñique entre frames consecutivos:

```python
# Guardar posición anterior del meñique
pinky_sum = pinky_coords[0] + pinky_coords[1]   # x + y del meñique
delta     = abs(pinky_sum - prev_sum)            # cuánto se movió

# Si el dedo índice está solo arriba Y el meñique se movió más de 30px → J
if dedos == [0, 0, 1, 0, 0, 0] and delta > 30:
    sign = "J"
```

---

### Anotación del frame

Después de clasificar la seña, OpenCV dibuja sobre el frame antes de devolverlo:

```python
# Rectángulo alrededor de la mano
cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

# Etiqueta con la letra detectada
cv2.putText(annotated, label, (x1 + 6, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
```

El color del bounding box cambia según la letra: **naranja** para J (movimiento), **azul-violeta** para el resto.

---

## 🖥️ El servidor Flask — `app.py`

Flask actúa como intermediario entre el navegador y el detector. El endpoint principal es:

```python
@app.route("/api/process_frame", methods=["POST"])
def process_frame():
    # 1. Recibir el frame en base64
    img_data = request.get_json()["frame"]

    # 2. Decodificar base64 → imagen numpy
    img_bytes = base64.b64decode(img_data.split(",", 1)[1])
    frame = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    # 3. Procesar con MediaPipe
    annotated, signs = detector.process_frame(frame)

    # 4. Devolver frame anotado + letra detectada
    _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return jsonify({
        "signs": signs,
        "history": history[-10:],
        "annotated_frame": base64.b64encode(buf).decode("utf-8")
    })
```

### Rutas disponibles

| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Devuelve la página principal |
| `/api/process_frame` | POST | Recibe frame → devuelve letra + frame anotado |
| `/api/clear_history` | GET/POST | Limpia el historial de señas |
| `/api/status` | GET | Estado actual (historial) |
| `/api/signs` | GET | Lista completa de señas soportadas |

---

## 🌐 El frontend — `app.js`

El navegador maneja toda la captura de video sin depender del servidor:

```javascript
// 1. Pedir permiso y abrir la cámara
mediaStream = await navigator.mediaDevices.getUserMedia({
    video: { width: 640, height: 480, facingMode: 'user' },
    audio: false
});
videoRaw.srcObject = mediaStream;

// 2. Loop continuo: capturar frame → enviar → mostrar resultado
async function sendFrame() {
    // Dibujar frame actual en canvas oculto
    captureCtx.drawImage(videoRaw, 0, 0);

    // Codificar como JPEG base64
    const frameB64 = captureCanvas.toDataURL('image/jpeg', 0.7);

    // Enviar al servidor
    const res  = await fetch('/api/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame: frameB64 })
    });

    const data = await res.json();

    // Mostrar el frame anotado que devolvió el servidor
    const img = new Image();
    img.onload = () => displayCtx.drawImage(img, 0, 0);
    img.src = 'data:image/jpeg;base64,' + data.annotated_frame;
}
```

---

## 🔤 Letras detectadas

| Método | Letras |
|---|---|
| Ángulos (principal) | `A` `E` `I` `O` `U` `B` `D` `F` `K` `L` `N` `P` `V` `W` `Y` |
| Landmarks (fallback) | `C` `G` `H` `M` `Q` `R` `S` `T` `X` |
| Movimiento | `J` |
| Gestos extra | `✊` `👍` `✌️` `🤘` `✋` |

---

## 🚀 Correr en local

```bash
# 1. Entrar a la carpeta del proyecto
cd señas

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python app.py

# 4. Abrir en el navegador
#    http://localhost:5000
```

> Requiere **Python 3.8 – 3.11**. MediaPipe aún no es compatible con Python 3.12+.

---

## ☁️ Deploy en Railway

Railway es una plataforma en la nube que permite publicar el proyecto con una URL pública, accesible desde cualquier dispositivo con internet.

**Pasos:**

1. Subir el proyecto a un repositorio de **GitHub**
2. Ir a [railway.app](https://railway.app) → crear cuenta gratuita
3. **New Project** → Deploy from GitHub repo
4. Seleccionar el repositorio → Railway detecta el `Procfile` automáticamente
5. En 2-3 minutos genera una URL pública tipo `https://tuapp.railway.app`

**Archivos de configuración incluidos:**

| Archivo | Para qué sirve |
|---|---|
| `Procfile` | Le dice a Railway cómo arrancar: `gunicorn app:app` |
| `runtime.txt` | Especifica `python-3.11.9` para el entorno de build |
| `requirements.txt` | Railway instala todas las dependencias automáticamente |

> El plan gratuito incluye **500 horas/mes**, más que suficiente para un proyecto de uso normal.

---

## 📦 Dependencias

```txt
flask==3.0.3
opencv-python-headless==4.10.0.84
mediapipe==0.10.14
numpy==1.26.4
gunicorn==22.0.0
```
