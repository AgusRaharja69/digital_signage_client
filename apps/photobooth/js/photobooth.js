/* ============================================================
   PHOTOBOOTH — photobooth.js  v4
   Full browser-side compositing using HTML Canvas.
   
   Flow:
     1. User picks frame
     2. Webcam starts
     3. 5s countdown × 3 → each capture stored as ImageBitmap
     4. Canvas: draw frame image, then draw each photo into slot position
     5. canvas.toBlob() → send to /photobooth/save → get URL
     6. Show result 10s → redirect home
   
   Slot positions (% of frame 1000×2000, same for all 3 frames):
     Slot 1: left=11.10%  top=22.05%  width=77.60%  height=18.20%
     Slot 2: left=11.10%  top=42.75%  width=77.60%  height=18.20%
     Slot 3: left=11.20%  top=63.45%  width=77.60%  height=18.20%
   ============================================================ */

'use strict';

/* ── Slot definitions as fractions of frame size ──────────────────────────── */
const SLOTS = [
    { left: 0.1110, top: 0.2205, width: 0.7760, height: 0.1820 },
    { left: 0.1110, top: 0.4275, width: 0.7760, height: 0.1820 },
    { left: 0.1120, top: 0.6345, width: 0.7760, height: 0.1820 },
];

/* ── State ──────────────────────────────────────────────────────────────────── */
const PB = {
    selectedFrame: null,      // filename
    capturedBitmaps: [],      // ImageBitmap objects
    currentShot:  0,
    stream:       null,
    countdownId:  null,
    resultId:     null,
    frameImage:   null,       // HTMLImageElement of selected frame
};

/* ── DOM ──────────────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── Screen ───────────────────────────────────────────────────────────────── */
function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    $(id).classList.add('active');
}

/* ══════════════════════════════════════════════════════════════
   SCREEN 1 — FRAME SELECT
   ══════════════════════════════════════════════════════════════ */
function selectFrame(el) {
    document.querySelectorAll('.frame-thumb').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
    PB.selectedFrame = el.dataset.frame;
}

async function startSession() {
    const sel = document.querySelector('.frame-thumb.selected');
    if (!sel) { alert('Pilih frame dulu!'); return; }

    PB.selectedFrame   = sel.dataset.frame;
    PB.capturedBitmaps = [];
    PB.currentShot     = 0;

    // Preload frame image
    PB.frameImage = await loadImage(`/photobooth/imgs/frames/${PB.selectedFrame}`);

    // Update UI
    $('frame-mini-img').src = `/photobooth/imgs/frames/${PB.selectedFrame}`;
    resetStrip();
    resetDots();
    showScreen('screen-capture');

    // Start webcam
    try {
        PB.stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
            audio: false
        });
        $('camera-feed').srcObject = PB.stream;
        await $('camera-feed').play();
        setStatus('Kamera siap!');
        setTimeout(startCountdown, 800);
    } catch (err) {
        setStatus('⚠ Gagal akses kamera: ' + err.message);
    }
}

/* ══════════════════════════════════════════════════════════════
   COUNTDOWN → CAPTURE
   ══════════════════════════════════════════════════════════════ */
function startCountdown() {
    const n = PB.currentShot + 1;
    $('shot-info').textContent = `Foto ${n} dari 3`;
    setDot(PB.currentShot, 'active');
    setStatus(`Bersiap untuk foto ${n}…`);

    let count = 5;
    const cdEl  = $('cam-countdown');
    const numEl = $('cd-number');

    cdEl.classList.remove('hidden');
    setCountdownNum(numEl, count);

    clearInterval(PB.countdownId);
    PB.countdownId = setInterval(() => {
        count--;
        if (count > 0) {
            setCountdownNum(numEl, count);
        } else {
            clearInterval(PB.countdownId);
            cdEl.classList.add('hidden');
            doCapture();
        }
    }, 1000);
}

function setCountdownNum(el, n) {
    el.textContent = n;
    el.style.animation = 'none';
    void el.offsetWidth;
    el.style.animation = 'countPop .45s cubic-bezier(.22,1,.36,1)';
}

async function doCapture() {
    const video = $('camera-feed');

    // Flash
    const flash = $('cam-flash');
    flash.classList.add('flashing');
    flash.addEventListener('animationend', () => flash.classList.remove('flashing'), { once: true });

    // Capture frame from video as ImageBitmap (full quality, no JPEG loss yet)
    const bitmap = await createImageBitmap(video);
    PB.capturedBitmaps.push(bitmap);

    // Update strip
    fillStrip(PB.currentShot, bitmap);
    setDot(PB.currentShot, 'done');
    setStatus(`Foto ${PB.currentShot + 1} diambil ✓`);

    PB.currentShot++;

    if (PB.currentShot < 3) {
        setTimeout(startCountdown, 1200);
    } else {
        setTimeout(composeInBrowser, 600);
    }
}

/* ══════════════════════════════════════════════════════════════
   BROWSER-SIDE COMPOSITING
   Draw photos into slot positions on the frame canvas.
   ══════════════════════════════════════════════════════════════ */
async function composeInBrowser() {
    stopCamera();
    showScreen('screen-compositing');

    await new Promise(r => setTimeout(r, 100)); // let screen render

    const frame  = PB.frameImage;
    const fw     = frame.naturalWidth;    // 1000
    const fh     = frame.naturalHeight;  // 2000

    const canvas = $('compose-canvas');
    canvas.width  = fw;
    canvas.height = fh;
    const ctx = canvas.getContext('2d');

    // 1. Draw black background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, fw, fh);

    // 2. Draw each captured photo into its slot (BEHIND the frame)
    for (let i = 0; i < 3; i++) {
        const slot   = SLOTS[i];
        const sx     = Math.round(slot.left   * fw);
        const sy     = Math.round(slot.top    * fh);
        const sw     = Math.round(slot.width  * fw);
        const sh     = Math.round(slot.height * fh);
        const bitmap = PB.capturedBitmaps[i];

        if (!bitmap) continue;

        const bw = bitmap.width;
        const bh = bitmap.height;

        // Cover-crop: find source rect that fills slot at correct aspect ratio
        const slotAR = sw / sh;
        const bitmapAR = bw / bh;
        let srcX, srcY, srcW, srcH;

        if (bitmapAR > slotAR) {
            // bitmap is wider → crop left/right
            srcH = bh;
            srcW = bh * slotAR;
            srcX = (bw - srcW) / 2;
            srcY = 0;
        } else {
            // bitmap is taller → crop top/bottom
            srcW = bw;
            srcH = bw / slotAR;
            srcX = 0;
            srcY = (bh - srcH) / 2;
        }

        ctx.save();
        ctx.beginPath();
        ctx.rect(sx, sy, sw, sh);
        ctx.clip();

        // Mirror horizontally (undo webcam mirror effect)
        ctx.translate(sx + sw, sy);
        ctx.scale(-1, 1);
        ctx.drawImage(bitmap, srcX, srcY, srcW, srcH, 0, 0, sw, sh);

        ctx.restore();
    }

    // 3. Draw frame ON TOP (covers decorative areas, keeps slots transparent)
    ctx.drawImage(frame, 0, 0, fw, fh);

    // 4. Draw header overlay: logo_univ + logo_sekolah side by side + school name below
    // 5. Draw footer overlay: barcode centered at bottom
    // Semua data dari window.PB_CONFIG yang di-inject dari database config
    await drawOverlays(ctx, fw, fh);

    // 6. Convert to blob and send to server to save
    canvas.toBlob(async (blob) => {
        try {
            const formData = new FormData();
            formData.append('image', blob, 'photobooth.jpg');
            formData.append('frame', PB.selectedFrame);

            const resp   = await fetch('/photobooth/save', {
                method: 'POST',
                body:   formData
            });
            const result = await resp.json();

            if (result.success) {
                showResult(result.url, result.drive_uploading);
            } else {
                showResult(canvas.toDataURL('image/jpeg', 0.95), false);
            }
        } catch (err) {
            console.error('Save error:', err);
            showResult(canvas.toDataURL('image/jpeg', 0.95), false);
        }
    }, 'image/jpeg', 0.95);
}

/* ══════════════════════════════════════════════════════════════
   RESULT SCREEN
   ══════════════════════════════════════════════════════════════ */
function showResult(url, driveUploading) {
    $('result-img').src = url;
    showScreen('screen-result');

    // Tampilkan badge status Drive jika upload sedang berjalan
    const driveBadge = $('drive-status');
    if (driveBadge) {
        if (driveUploading) {
            driveBadge.className = 'drive-badge uploading';
            driveBadge.innerHTML = '<span class="drive-spin">⟳</span> Mengirim ke Google Drive…';
            driveBadge.style.display = 'flex';
        } else {
            driveBadge.style.display = 'none';
        }
    }

    const bar  = $('result-bar');
    const secEl = $('result-sec');
    bar.style.transition = 'none';
    bar.style.width      = '100%';

    let remaining = 10;
    secEl.textContent = remaining;

    requestAnimationFrame(() => requestAnimationFrame(() => {
        bar.style.transition = 'width 10s linear';
        bar.style.width      = '0%';
    }));

    clearInterval(PB.resultId);
    PB.resultId = setInterval(() => {
        remaining--;
        secEl.textContent = remaining;
        if (remaining <= 0) {
            clearInterval(PB.resultId);
            goHome();
        }
    }, 1000);
}

function goHome() {
    clearInterval(PB.resultId);
    clearInterval(PB.countdownId);
    stopCamera();
    window.location.href = '/';
}

/* ══════════════════════════════════════════════════════════════
   CANVAS OVERLAYS
   Gambar header (logo + nama sekolah) dan footer (barcode)
   di atas frame yang sudah jadi.
   
   Layout pada canvas 1000×2000:
   ┌─────────────────────────────┐
   │  [logo1]  [logo2]           │  ← header area ~0–22% (y: 0–440)
   │   NAMA SEKOLAH              │
   │   foto 1                    │
   │   foto 2                    │
   │   foto 3                    │
   │      [ BARCODE ]            │  ← footer area ~88–100% (y: 1760–2000)
   └─────────────────────────────┘
   ══════════════════════════════════════════════════════════════ */
async function drawOverlays(ctx, fw, fh) {
    const cfg = window.PB_CONFIG || {};

    // ── HEADER: dua logo bersebelahan ─────────────────────────────────────
    const HEADER_TOP    = 30;        // px dari atas canvas
    const HEADER_H      = 160;       // tinggi area logo
    const LOGO_W        = 140;       // lebar tiap logo
    const LOGO_H        = 140;       // tinggi tiap logo
    const LOGO_GAP      = 32;        // jarak antar logo
    const totalLogoW    = LOGO_W * 2 + LOGO_GAP;
    const logoStartX    = (fw - totalLogoW) / 2;

    // Gambar logo universitas
    if (cfg.logoUniv) {
        try {
            const img = await loadImage(cfg.logoUniv);
            const logoY = HEADER_TOP + (HEADER_H - LOGO_H) / 2;
            const { dx, dy, dw, dh } = fitContain(
                img.naturalWidth, img.naturalHeight,
                logoStartX, logoY, LOGO_W, LOGO_H
            );
            ctx.drawImage(img, dx, dy, dw, dh);
        } catch(e) { console.warn('logo_univ load failed', e); }
    }

    // Gambar logo sekolah
    if (cfg.logoSekolah) {
        try {
            const img = await loadImage(cfg.logoSekolah);
            const logoX = logoStartX + LOGO_W + LOGO_GAP;
            const logoY = HEADER_TOP + (HEADER_H - LOGO_H) / 2;
            const { dx, dy, dw, dh } = fitContain(
                img.naturalWidth, img.naturalHeight,
                logoX, logoY, LOGO_W, LOGO_H
            );
            ctx.drawImage(img, dx, dy, dw, dh);
        } catch(e) { console.warn('logo_sekolah load failed', e); }
    }

    // ── HEADER: nama sekolah di bawah logo ───────────────────────────────
    if (cfg.schoolName) {
        const textY = HEADER_TOP + HEADER_H + 18;
        const fontSize = Math.round(fw * 0.052);   // ~52px pada canvas 1000px

        ctx.save();
        ctx.font         = `700 ${fontSize}px 'Arial', sans-serif`;
        ctx.fillStyle    = '#FFFFFF';
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';

        // Drop shadow agar terbaca di atas background gelap/terang
        ctx.shadowColor   = 'rgba(0,0,0,0.7)';
        ctx.shadowBlur    = 8;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;

        // Uppercase otomatis
        ctx.fillText(cfg.schoolName.toUpperCase(), fw / 2, textY);
        ctx.restore();
    }

    // ── FOOTER: barcode di tengah bawah ──────────────────────────────────
    if (cfg.barcodeUrl) {
        try {
            const img = await loadImage(cfg.barcodeUrl);

            const BARCODE_W  = 200;
            const BARCODE_H  = 200;
            const BARCODE_Y  = fh - BARCODE_H - 36;   // 36px dari bawah
            const BARCODE_X  = (fw - BARCODE_W) / 2;

            // Background putih agar barcode bisa di-scan
            ctx.save();
            ctx.fillStyle = '#FFFFFF';
            const PAD = 12;
            ctx.fillRect(BARCODE_X - PAD, BARCODE_Y - PAD, BARCODE_W + PAD*2, BARCODE_H + PAD*2);

            const { dx, dy, dw, dh } = fitContain(
                img.naturalWidth, img.naturalHeight,
                BARCODE_X, BARCODE_Y, BARCODE_W, BARCODE_H
            );
            ctx.drawImage(img, dx, dy, dw, dh);
            ctx.restore();
        } catch(e) { console.warn('barcode load failed', e); }
    }
}

/* Hitung posisi gambar agar fit di dalam kotak (object-fit: contain, centered). */
function fitContain(imgW, imgH, boxX, boxY, boxW, boxH) {
    const scale = Math.min(boxW / imgW, boxH / imgH);
    const dw    = imgW * scale;
    const dh    = imgH * scale;
    const dx    = boxX + (boxW - dw) / 2;
    const dy    = boxY + (boxH - dh) / 2;
    return { dx, dy, dw, dh };
}


function stopCamera() {
    if (PB.stream) {
        PB.stream.getTracks().forEach(t => t.stop());
        PB.stream = null;
        $('camera-feed').srcObject = null;
    }
}

function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload  = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

function setStatus(msg) {
    $('status-bar').textContent = msg;
}

/* Strip */
function resetStrip() {
    for (let i = 0; i < 3; i++) {
        const s = $(`strip-${i}`);
        const c = s.querySelector('canvas');
        if (c) c.remove();
        const sp = s.querySelector('span');
        if (!sp) { const e = document.createElement('span'); e.textContent = i+1; s.appendChild(e); }
        else sp.style.display = '';
        s.classList.remove('filled');
    }
}

function fillStrip(index, bitmap) {
    const slot = $(`strip-${index}`);
    slot.querySelector('span').style.display = 'none';
    slot.classList.add('filled');

    const c   = document.createElement('canvas');
    const sw  = slot.clientWidth  || 160;
    const sh  = slot.clientHeight || 70;
    c.width   = sw;
    c.height  = sh;
    const ctx = c.getContext('2d');

    // Cover-crop bitmap into strip slot
    const bw = bitmap.width, bh = bitmap.height;
    const scale  = Math.max(sw/bw, sh/bh);
    const scaledW = bw*scale, scaledH = bh*scale;
    const ox = (scaledW-sw)/2, oy = (scaledH-sh)/2;

    // Mirror
    ctx.save();
    ctx.translate(sw, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(bitmap, -ox/scale, oy/scale, sw/scale, sh/scale, 0, 0, sw, sh);
    ctx.restore();

    slot.appendChild(c);
}

/* Dots */
function resetDots() {
    ['dot-0','dot-1','dot-2'].forEach(id => {
        const d = $(id);
        d.className = 'dot';
    });
}

function setDot(index, state) {
    const d = $(`dot-${index}`);
    d.className = 'dot ' + state;
}

/* ── Init ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    const first = document.querySelector('.frame-thumb');
    if (first) PB.selectedFrame = first.dataset.frame;
    showScreen('screen-idle');
});