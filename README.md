# 🤟 Detector de Lenguaje de Señas - PROYECTO SENATI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-0097A7?style=for-the-badge&logo=google&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.10-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)

**Reconocimiento de letras del abecedario en lenguaje de señas usando visión por computadora, directamente desde el navegador.**

</div>

---

## ¿Qué es este proyecto?

Es una aplicación web que usa la cámara del dispositivo para detectar en tiempo real las letras del abecedario expresadas en lenguaje de señas. El usuario abre la app en el navegador, presiona Iniciar, y el sistema identifica qué letra está haciendo con la mano.

No requiere instalar nada extra más allá de las dependencias de Python. Funciona desde cualquier navegador moderno con cámara.

---

## ¿Para qué sirve?

- Como herramienta de aprendizaje del lenguaje de señas
- Para practicar el abecedario y recibir retroalimentación visual inmediata
- Como base para proyectos más avanzados de comunicación inclusiva
- Como demostración de visión por computadora aplicada

---

## 📁 Estructura del proyecto

```
señas/
│
├── app.py                  # Servidor Flask — rutas y lógica principal
├── sign_detector.py        # Motor de detección — ángulos + MediaPipe
├── requirements.txt        # Dependencias de Python
├── Procfile                # Comando de arranque para Railway
├── runtime.txt             # Versión de Python para deploy
│
├── templates/
│   └── index.html          # Interfaz web completa
│
└── static/
    ├── css/
    │   └── style.css       # Estilos y diseño
    └── js/
        └── app.js          # Lógica del frontend (cámara, envío de frames)
```

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Versión | Para qué se usó |
|---|---|---|
| **Python** | 3.11 | Lenguaje principal del backend |
| **Flask** | 3.0 | Servidor web y API REST |
| **MediaPipe** | 0.10 | Detección de 21 landmarks de la mano |
| **OpenCV Headless** | 4.10 | Procesamiento de imágenes y anotación de frames |
| **NumPy** | 1.26 | Cálculo de vectores y ángulos |
| **Gunicorn** | 22.0 | Servidor WSGI para producción |
| **HTML / CSS / JS** | — | Frontend sin frameworks adicionales |

> Se usa `opencv-python-headless` en lugar de `opencv-python` porque la versión headless no necesita librerías de pantalla (Qt, GTK), que no existen en servidores en la nube.

---

## ⚙️ Cómo funciona — paso a paso

### 1. El navegador captura la cámara

```
Navegador → getUserMedia API → stream de video local
```

Al presionar **Iniciar**, el navegador pide permiso para usar la cámara usando la API nativa `getUserMedia`. El video se renderiza en un elemento `<canvas>` invisible.

Este enfoque permite que la app funcione desplegada en la nube, ya que el servidor no necesita acceso a ninguna cámara física.

---

### 2. Los frames se envían al servidor

```
Canvas (frame actual) → JPEG base64 → POST /api/process_frame
```

Cada frame del video se captura con `canvas.toDataURL('image/jpeg')`, se codifica en base64 y se manda al servidor Flask como JSON. Esto sucede en un loop continuo sincronizado con `requestAnimationFrame`.

---

### 3. MediaPipe detecta la mano

```
Frame JPEG → OpenCV decode → MediaPipe → 21 landmarks
```

El servidor decodifica el frame, lo pasa por MediaPipe Hands que devuelve las coordenadas de **21 puntos clave** de la mano:

```
Punta del dedo, articulación media, base de cada dedo, muñeca...
```

<div align="center">

```
        8   12  16  20
        |   |   |   |
        7   11  15  19
        |   |   |   |
    4   6   10  14  18
    |   5   9   13  17
    3       |
    |       0 (muñeca)
    2
    |
    1
```

</div>

---

### 4. Se calculan los ángulos de cada dedo

```python
# Ley del coseno sobre los 3 puntos de cada dedo
angle = degrees(acos((l1² + l3² - l2²) / (2 * l1 * l3)))
```

Con los landmarks se calcula el **ángulo en la articulación media** de cada dedo usando la ley del coseno. Esto determina si el dedo está extendido o doblado:

- Ángulo **> 90°** → dedo **extendido** → `1`
- Ángulo **≤ 90°** → dedo **doblado** → `0`

El resultado es un array de 6 bits:

```
[pulgar_ext, pulgar_int, meñique, anular, medio, índice]
```

---

### 5. El patrón se compara con el abecedario

```python
if dedos == [1, 1, 0, 0, 0, 0]: return "A"
if dedos == [0, 0, 0, 0, 0, 0]: return "E"
if dedos == [0, 0, 1, 0, 0, 0]: return "I"
if dedos == [1, 0, 1, 0, 0, 0]: return "O"
if dedos == [0, 0, 1, 0, 0, 1]: return "U"
# ... y así con todas las letras
```

Si no hay match en la clasificación por ángulos, se usa un **método fallback** basado en distancias y posiciones relativas entre landmarks para cubrir más letras.

---

### 6. Detección de movimiento (letra J)

La letra J requiere movimiento del meñique. Se detecta así:

```python
pinky_sum = pinky_coords[0] + pinky_coords[1]
delta     = abs(pinky_sum - prev_sum)

if dedos == [0, 0, 1, 0, 0, 0] and delta > 30:
    sign = "J"
```

Se guarda la posición del meñique en cada frame y si el desplazamiento supera 30 píxeles entre frames, se detecta como J.

---

### 7. El frame anotado vuelve al navegador

```
Frame anotado (OpenCV) → JPEG → base64 → JSON → canvas del navegador
```

El servidor dibuja el bounding box y la letra sobre el frame con OpenCV, lo codifica en base64 y lo devuelve en la respuesta JSON. El navegador lo muestra en el `<canvas>` visible.

---

## 🔤 Letras detectadas

| Método | Letras |
|---|---|
| Por ángulos (principal) | A, E, I, O, U, B, D, F, K, L, N, P, V, W, Y |
| Por landmarks (fallback) | C, G, H, M, Q, R, S, T, X, U, V |
| Por movimiento | J |

---

## 🚀 Correr en local

**1. Clonar o descargar el proyecto**

```bash
git clone <url-del-repo>
cd señas
```

**2. Instalar dependencias**

```bash
pip install -r requirements.txt
```

> Requiere **Python 3.8 – 3.11**. MediaPipe no soporta Python 3.12+.

**3. Ejecutar**

```bash
python app.py
```

**4. Abrir en el navegador**

```
http://localhost:5000
```

---

## ☁️ Deploy en Railway

Railway es una plataforma en la nube que permite desplegar el proyecto para que funcione desde cualquier dispositivo sin correrlo local.

**Pasos:**

1. Subir la carpeta `señas/` a un repositorio de **GitHub**
2. Entrar a [railway.app](https://railway.app) y crear una cuenta gratuita
3. Nuevo proyecto → **Deploy from GitHub repo**
4. Seleccionar el repositorio
5. Railway detecta el `Procfile` automáticamente y despliega
6. En pocos minutos genera una URL pública: `https://tuapp.railway.app`

> El plan gratuito incluye **500 horas/mes**, suficiente para uso normal.

**Archivos necesarios para el deploy** (ya incluidos):

```
Procfile      → le dice a Railway cómo arrancar la app
runtime.txt   → especifica la versión de Python
requirements.txt → instala las dependencias automáticamente
```

---

## 🖥️ API del servidor

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Página principal |
| `/api/process_frame` | POST | Recibe frame en base64, devuelve letra + frame anotado |
| `/api/clear_history` | GET/POST | Limpia el historial de señas |
| `/api/status` | GET | Estado actual del servidor |
| `/api/signs` | GET | Lista de todas las señas soportadas |

---

## 📦 Dependencias

```txt
flask==3.0.3
opencv-python-headless==4.10.0.84
mediapipe==0.10.14
numpy==1.26.4
gunicorn==22.0.0
```
