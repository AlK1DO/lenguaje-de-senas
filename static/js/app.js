/* ── Señas — Frontend (getUserMedia + base64 frames) ────────────────────── */

// DOM
const startBtn         = document.getElementById('startBtn');
const stopBtn          = document.getElementById('stopBtn');
const videoRaw         = document.getElementById('videoRaw');
const captureCanvas    = document.getElementById('captureCanvas');
const displayCanvas    = document.getElementById('displayCanvas');
const videoPlaceholder = document.getElementById('videoPlaceholder');
const detectionDisplay = document.getElementById('detectionDisplay');
const historyList      = document.getElementById('historyList');
const clearHistoryBtn  = document.getElementById('clearHistoryBtn');
const clearWordBtn     = document.getElementById('clearWordBtn');
const addLetterBtn     = document.getElementById('addLetterBtn');
const wordDisplay      = document.getElementById('wordDisplay');
const statusDot        = document.getElementById('statusDot');
const statusText       = document.getElementById('statusText');
const heroChar         = document.getElementById('heroChar');
const heroSign         = document.getElementById('heroSign');
const liveDot          = document.getElementById('liveDot');
const fpsCounter       = document.getElementById('fpsCounter');

const captureCtx   = captureCanvas.getContext('2d');
const displayCtx   = displayCanvas.getContext('2d');

let mediaStream    = null;
let loopActive     = false;
let lastSigns      = [];
let lastHistory    = [];
let currentWord    = '';
let lastDetected   = null;

// FPS tracking
let frameCount     = 0;
let fpsTimer       = Date.now();

// ── Navegación ──────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
    if (tab === 'signs') loadSigns();
  });
});

// ── Iniciar cámara ──────────────────────────────────────────────────────────
startBtn.addEventListener('click', async () => {
  setStatus('connecting', 'Solicitando cámara...');
  startBtn.classList.add('hidden');

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    });

    videoRaw.srcObject = mediaStream;
    await videoRaw.play();

    // Ajustar canvas al tamaño real del video
    const { videoWidth: vw, videoHeight: vh } = videoRaw;
    captureCanvas.width  = vw || 640;
    captureCanvas.height = vh || 480;
    displayCanvas.width  = vw || 640;
    displayCanvas.height = vh || 480;

    videoPlaceholder.classList.add('hidden');
    displayCanvas.classList.remove('hidden');
    stopBtn.classList.remove('hidden');

    setStatus('streaming', 'En vivo');

    loopActive = true;
    frameCount = 0;
    fpsTimer   = Date.now();
    processLoop();

  } catch (err) {
    console.error(err);
    setStatus('error', 'Sin acceso a cámara');
    startBtn.classList.remove('hidden');
  }
});

// ── Detener cámara ──────────────────────────────────────────────────────────
stopBtn.addEventListener('click', stopCamera);

function stopCamera() {
  loopActive = false;

  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }

  displayCanvas.classList.add('hidden');
  videoPlaceholder.classList.remove('hidden');
  stopBtn.classList.add('hidden');
  startBtn.classList.remove('hidden');

  setStatus('idle', 'Listo');
  clearDetection();
  lastSigns = [];
}

// ── Loop de procesamiento ───────────────────────────────────────────────────
// Captura un frame, lo manda al servidor y muestra el resultado anotado.
// Usa recursión con requestAnimationFrame para no saturar el servidor.
let processing = false;

async function processLoop() {
  if (!loopActive) return;

  if (!processing) {
    processing = true;
    await sendFrame();
    processing = false;
  }

  requestAnimationFrame(processLoop);
}

async function sendFrame() {
  if (!videoRaw.videoWidth) return;

  // Dibujar frame en canvas oculto
  captureCtx.drawImage(videoRaw, 0, 0, captureCanvas.width, captureCanvas.height);

  // Codificar como JPEG base64
  const frameB64 = captureCanvas.toDataURL('image/jpeg', 0.7);

  try {
    const res = await fetch('/api/process_frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame: frameB64 }),
    });

    if (!res.ok) return;

    const data = await res.json();

    // Mostrar frame anotado en el canvas visible
    if (data.annotated_frame) {
      const img = new Image();
      img.onload = () => displayCtx.drawImage(img, 0, 0);
      img.src = 'data:image/jpeg;base64,' + data.annotated_frame;
    }

    // FPS
    frameCount++;
    const now = Date.now();
    if (now - fpsTimer >= 1000) {
      fpsCounter.textContent = `${frameCount} FPS`;
      frameCount = 0;
      fpsTimer   = now;
    }

    if (data.signs !== undefined)   updateDetection(data.signs);
    if (data.history !== undefined) updateHistory(data.history);

  } catch (err) {
    // Ignorar errores de red puntuales
  }
}

// ── Controles de historial y palabra ────────────────────────────────────────
clearHistoryBtn.addEventListener('click', async () => {
  await fetch('/api/clear_history');
  renderHistory([]);
  lastHistory = [];
});

clearWordBtn.addEventListener('click', () => {
  currentWord = '';
  renderWord();
});

addLetterBtn.addEventListener('click', () => {
  if (lastDetected && lastDetected !== '?') {
    const letter = lastDetected.replace(/[^A-Za-z]/g, '');
    if (letter) {
      currentWord += letter.toUpperCase();
      renderWord();
    }
  }
});

// ── Detección ────────────────────────────────────────────────────────────────
function updateDetection(signs) {
  const key = signs.join(',');
  if (key === lastSigns.join(',')) return;
  lastSigns = signs;

  if (!signs.length) { clearDetection(); return; }

  const first = signs[0];
  if (first !== lastDetected) {
    lastDetected = first;
    heroChar.textContent = first;
    heroSign.classList.remove('pop');
    void heroSign.offsetWidth;
    heroSign.classList.add('pop');
    addLetterBtn.disabled = false;
  }

  detectionDisplay.innerHTML = signs
    .map(s => `<span class="chip">${s}</span>`)
    .join('');

  liveDot.classList.add('active');
  setTimeout(() => liveDot.classList.remove('active'), 600);
}

function clearDetection() {
  detectionDisplay.innerHTML = '<span class="no-detect">Sin señas</span>';
  heroChar.textContent = '?';
  lastDetected = null;
  addLetterBtn.disabled = true;
}

// ── Historial ────────────────────────────────────────────────────────────────
function updateHistory(history) {
  if (JSON.stringify(history) === JSON.stringify(lastHistory)) return;
  lastHistory = [...history];
  renderHistory(history);
}

function renderHistory(history) {
  if (!history || !history.length) {
    historyList.innerHTML = `
      <div class="history-empty">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>
        <p>El historial aparecerá aquí</p>
      </div>`;
    return;
  }

  historyList.innerHTML = [...history].reverse().map((sign, i) => `
    <div class="history-row">
      <span class="history-sign">${sign}</span>
      <span class="history-time">${i === 0 ? 'ahora' : `hace ${i * 2}s`}</span>
    </div>
  `).join('');
}

// ── Palabra ──────────────────────────────────────────────────────────────────
function renderWord() {
  wordDisplay.innerHTML = currentWord
    ? `<span>${currentWord}</span>`
    : '<span class="word-placeholder">—</span>';
}

// ── Estado ───────────────────────────────────────────────────────────────────
function setStatus(state, text) {
  statusDot.className = 'status-indicator';
  if (state === 'streaming') statusDot.classList.add('streaming');
  if (state === 'error')     statusDot.classList.add('error');
  statusText.textContent = text;
}

// ── Abecedario ───────────────────────────────────────────────────────────────
let signsLoaded = false;

async function loadSigns() {
  if (signsLoaded) return;
  try {
    const res   = await fetch('/api/signs');
    const signs = await res.json();
    const grid  = document.getElementById('signsGrid');

    grid.innerHTML = signs.map(s => `
      <div class="sign-tile ${s.static ? '' : 'motion'}" data-type="${s.static ? 'static' : 'motion'}">
        <span class="tile-letter">${s.letter}</span>
        <span class="tile-desc">${s.description}</span>
        ${!s.static ? '<span class="motion-tag">Movimiento</span>' : ''}
      </div>
    `).join('');

    signsLoaded = true;
  } catch (e) {
    console.error('Error cargando señas:', e);
  }
}

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('.sign-tile').forEach(tile => {
      if (filter === 'all') {
        tile.classList.remove('hidden-tile');
      } else {
        tile.classList.toggle('hidden-tile', tile.dataset.type !== filter);
      }
    });
  });
});

// ── Init ─────────────────────────────────────────────────────────────────────
setStatus('idle', 'Listo');
