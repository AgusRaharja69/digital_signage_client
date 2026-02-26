/* ============================================================
   PHOTOBOOTH — photobooth.js
   State machine:
     IDLE → CAPTURE (x3) → PROCESSING → RESULT (10s) → HOME
   ============================================================ */

'use strict';

/* ── State ────────────────────────────────────────────────── */
const PB = {
    selectedFrame: null,      // filename e.g. "frame1.png"
    capturedPhotos: [],       // array of base64 data-URLs (max 3)
    currentShot: 0,           // 0, 1, 2
    countdownValue: 5,
    countdownTimer: null,
    resultTimer: null,
    stream: null,             // MediaStream
};

/* ── DOM refs ─────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── Screens ─────────────────────────────────────────────── */
function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const el = $(id);
    if (el) el.classList.add('active');
}

/* ══════════════════════════════════════════════════════════
   SCREEN 1 — IDLE / FRAME SELECT
   ══════════════════════════════════════════════════════════ */
function selectFrame(el) {
    document.querySelectorAll('.frame-thumb').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
    PB.selectedFrame = el.dataset.frame;
}

async function startSession() {
    // Determine selected frame
    const sel = document.querySelector('.frame-thumb.selected');
    if (!sel) { alert('Pilih frame terlebih dahulu!'); return; }
    PB.selectedFrame = sel.dataset.frame;

    // Show selected frame in capture screen
    $('selected-frame-thumb').src = `/photobooth/imgs/frames/${PB.selectedFrame}`;

    // Reset state
    PB.capturedPhotos = [];
    PB.currentShot    = 0;
    resetStripSlots();
    resetDots();

    showScreen('screen-capture');

    // Start webcam
    try {
        PB.stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
        });
        $('camera-feed').srcObject = PB.stream;
        await $('camera-feed').play();
    } catch (err) {
        console.error('Camera error:', err);
        $('capture-status').textContent = '⚠ Tidak bisa akses kamera: ' + err.message;
        return;
    }

    // Start first countdown
    setTimeout(() => beginCountdown(), 800);
}

/* ══════════════════════════════════════════════════════════
   COUNTDOWN → CAPTURE
   ══════════════════════════════════════════════════════════ */
function beginCountdown() {
    const shotNum = PB.currentShot + 1;
    $('photo-counter').textContent = `Foto ${shotNum} dari 3`;
    setDotActive(PB.currentShot);

    let count = 5;
    $('countdown-number').textContent = count;
    $('countdown-overlay').classList.add('active');
    $('capture-status').textContent = `Bersiap untuk foto ${shotNum}…`;

    clearInterval(PB.countdownTimer);
    PB.countdownTimer = setInterval(() => {
        count--;
        // Re-trigger pop animation
        const el = $('countdown-number');
        el.textContent = count;
        el.style.animation = 'none';
        void el.offsetWidth; // reflow
        el.style.animation = 'countPop .4s cubic-bezier(.22,1,.36,1)';

        if (count <= 0) {
            clearInterval(PB.countdownTimer);
            $('countdown-overlay').classList.remove('active');
            capturePhoto();
        }
    }, 1000);
}

function capturePhoto() {
    const video    = $('camera-feed');
    const canvas   = $('snapshot-canvas');
    const ctx      = canvas.getContext('2d');

    canvas.width  = video.videoWidth  || 1280;
    canvas.height = video.videoHeight || 720;

    // Mirror horizontally (undo the CSS scaleX(-1) so saved photo is normal)
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataURL = canvas.toDataURL('image/jpeg', 0.92);
    PB.capturedPhotos.push(dataURL);

    // Flash
    const flash = $('camera-flash');
    flash.classList.add('flash-anim');
    flash.addEventListener('animationend', () => flash.classList.remove('flash-anim'), { once: true });

    // Update strip slot
    fillStripSlot(PB.currentShot, dataURL);
    setDotDone(PB.currentShot);

    $('capture-status').textContent = `Foto ${PB.currentShot + 1} diambil! ✓`;

    PB.currentShot++;

    if (PB.currentShot < 3) {
        // Next shot after 1.5s pause
        setTimeout(() => beginCountdown(), 1500);
    } else {
        // All 3 done — compose
        setTimeout(() => composeAndSave(), 1000);
    }
}

/* ══════════════════════════════════════════════════════════
   COMPOSE & SAVE
   ══════════════════════════════════════════════════════════ */
async function composeAndSave() {
    // Stop camera
    stopCamera();

    showScreen('screen-processing');

    try {
        const resp = await fetch('/photobooth/compose', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                photos: PB.capturedPhotos,
                frame:  PB.selectedFrame
            })
        });

        const result = await resp.json();

        if (!result.success) {
            throw new Error(result.error || 'Compose failed');
        }

        showResultScreen(result.url);

    } catch (err) {
        console.error('Compose error:', err);
        alert('Gagal menyusun foto: ' + err.message);
        goHome();
    }
}

/* ══════════════════════════════════════════════════════════
   RESULT SCREEN (10s countdown)
   ══════════════════════════════════════════════════════════ */
function showResultScreen(imageUrl) {
    $('result-img').src = imageUrl;
    showScreen('screen-result');

    // Countdown bar
    const bar  = $('result-bar');
    const secEl= $('result-sec');
    bar.style.transition = 'none';
    bar.style.width = '100%';

    let remaining = 10;
    secEl.textContent = remaining;

    // Trigger CSS transition
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            bar.style.transition = 'width 10s linear';
            bar.style.width      = '0%';
        });
    });

    clearInterval(PB.resultTimer);
    PB.resultTimer = setInterval(() => {
        remaining--;
        secEl.textContent = remaining;
        if (remaining <= 0) {
            clearInterval(PB.resultTimer);
            goHome();
        }
    }, 1000);
}

function goHome() {
    clearInterval(PB.resultTimer);
    clearInterval(PB.countdownTimer);
    stopCamera();
    window.location.href = '/';
}

/* ══════════════════════════════════════════════════════════
   HELPERS
   ══════════════════════════════════════════════════════════ */
function stopCamera() {
    if (PB.stream) {
        PB.stream.getTracks().forEach(t => t.stop());
        PB.stream = null;
        $('camera-feed').srcObject = null;
    }
}

function fillStripSlot(index, dataURL) {
    const slot = $(`strip-${index}`);
    if (!slot) return;
    slot.classList.add('filled');
    const img = document.createElement('img');
    img.src = dataURL;
    // Remove slot-num span
    slot.querySelector('.slot-num')?.remove();
    slot.appendChild(img);
}

function resetStripSlots() {
    for (let i = 0; i < 3; i++) {
        const slot = $(`strip-${i}`);
        if (!slot) continue;
        slot.classList.remove('filled');
        const img = slot.querySelector('img');
        if (img) img.remove();
        if (!slot.querySelector('.slot-num')) {
            const span = document.createElement('span');
            span.className = 'slot-num';
            span.textContent = i + 1;
            slot.appendChild(span);
        }
    }
}

function resetDots() {
    for (let i = 0; i < 3; i++) {
        const dot = $(`dot-${i}`);
        if (dot) { dot.classList.remove('done', 'active'); }
    }
}

function setDotActive(index) {
    resetDots();
    for (let i = 0; i < index; i++) setDotDone(i);
    const dot = $(`dot-${index}`);
    if (dot) dot.classList.add('active');
}

function setDotDone(index) {
    const dot = $(`dot-${index}`);
    if (dot) { dot.classList.remove('active'); dot.classList.add('done'); }
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    // Set first frame as selected by default
    const first = document.querySelector('.frame-thumb');
    if (first) {
        PB.selectedFrame = first.dataset.frame;
    }
    showScreen('screen-idle');
});