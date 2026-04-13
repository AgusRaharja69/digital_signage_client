/* ============================================================
   DIGITAL SIGNAGE — script.js  v3 (memory-safe)
   - Video elements properly paused + src cleared before removal
   - RAF agenda loop uses cancelAnimationFrame handle
   - All timers/intervals tracked and cleared
   - No DOM node accumulation
   - Page Visibility API: pause video when tab hidden
   ============================================================ */

'use strict';

/* ============================================================
   PERIODIC RELOAD — cegah OOM error code 5 di Raspberry Pi
   Chromium reload otomatis setiap RELOAD_INTERVAL_MS.
   Default: 6 jam. Hanya reload saat tidak ada video yang play.
   ============================================================ */
const RESTART_INTERVAL_MS = 6 * 60 * 60 * 1000; // 6 jam

function schedulePeriodicRestart() {
    setTimeout(async () => {
        const isVideoPlaying = document.body.classList.contains('video-playing');
        if (isVideoPlaying) {
            // Tunda sampai video selesai, cek lagi 1 menit
            console.log('[Restart] Video sedang play, tunda 1 menit');
            setTimeout(schedulePeriodicRestart, 60 * 1000);
            return;
        }
        console.log('[Restart] Meminta server restart Chromium...');
        try {
            await fetch('/api/restart-browser', { method: 'POST' });
        } catch(e) {
            // Normal — Chromium sudah mati sebelum response diterima
        }
    }, RESTART_INTERVAL_MS);
}

const STATE = {
    templates: window.SIGNAGE_DATA?.templates || [],
    ads:       window.SIGNAGE_DATA?.advertisements || [],
    agendas:   window.SIGNAGE_DATA?.agendas || [],

    // ⑤ Combined play queue: semua templates dulu, lalu ads, lalu loop
    queue:                [],
    currentIndex:         0,

    // Legacy ad popup (dinonaktifkan, tapi kode tetap ada)
    currentAdIndex:       0,

    templateTimer:  null,
    adTimer:        null,
    adTriggerTimer: null,
    _badgeTimer:    null,
    _adCdInterval:  null,
    _agendaRAF:     null,

    advancing: false,
};

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Digital Signage v3 (memory-safe) initialized');
    console.log('Templates:', STATE.templates.length);
    console.log('Ads:', STATE.ads.length);

    initDateTime();
    initAgendaScroll();
    initNewsScroll();
    initAgendaClickHandlers();
    initFloatingMenu();
    initAdHandlers();
    // initAutoplayGate();
    //startTemplateRotation();
    // Tunggu autoplay unlocker, lalu mulai rotation
    const unlocker = document.getElementById('autoplay-unlocker');
    if (unlocker) {
        unlocker.play()
            .then(() => {
                console.log('[Autoplay] Unlocked');
                startTemplateRotation();
            })
            .catch(() => {
                // Flag belum aktif — tetap coba mulai
                console.warn('[Autoplay] Blocked, starting anyway');
                startTemplateRotation();
            });
    } else {
        startTemplateRotation();
    }

    // Auto-reload setiap 6 jam untuk cegah OOM (Aw Snap error code 5)
    schedulePeriodicRestart();
});

function initAutoplayGate() {
    const gate = document.getElementById('autoplay-gate');
    if (!gate) {
        // Tidak ada gate di DOM — langsung mulai
        startTemplateRotation();
        return;
    }

    // Coba silent unlock dulu (tab sudah punya gesture sebelumnya / Chromium flag aktif)
    const probe = document.createElement('video');
    probe.muted = true;
    probe.src   = 'data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28ybXA0MAAAAA==';
    probe.play()
        .then(() => {
            probe.pause();
            gate.remove();
            startTemplateRotation();
            console.log('[Gate] Autoplay diizinkan — langsung mulai');
        })
        .catch(() => {
            // Butuh gesture — tampilkan gate
            gate.style.display = 'flex';
            console.log('[Gate] Menunggu gesture pengguna...');
        });

    const unlock = () => {
        gate.style.opacity = '0';
        gate.style.transition = 'opacity 0.4s';
        setTimeout(() => gate.remove(), 400);
        startTemplateRotation();
        console.log('[Gate] Gesture diterima — memulai tampilan');
    };

    gate.addEventListener('click',      unlock, { once: true });
    gate.addEventListener('touchstart', unlock, { once: true });
    gate.addEventListener('keydown',    unlock, { once: true });
}

/* ============================================================
   DATE / TIME + SCHEDULE CHECK (clock-based)
   Cek jadwal standby setiap detik ke-0 saat menit berganti.
   Menggunakan nilai dari SIGNAGE_DATA yang di-inject Flask,
   diperbarui dari server setiap 60 detik via fetchScheduleConfig().
   ============================================================ */

// Nilai jadwal — dari Flask inject, diupdate fetchScheduleConfig
let SCHED_OFF = window.SIGNAGE_DATA?.time_off || '23:59';
let SCHED_ON  = window.SIGNAGE_DATA?.time_on  || '00:00';

// Sync jadwal terbaru dari DB setiap 60 detik (hanya update variabel, tidak redirect)
async function fetchScheduleConfig() {
    try {
        const resp = await fetch('/api/schedule/status');
        if (!resp.ok) return;
        const data = await resp.json();
        SCHED_OFF = data.time_off || SCHED_OFF;
        SCHED_ON  = data.time_on  || SCHED_ON;
    } catch (e) { /* tetap pakai nilai sebelumnya */ }
}

function initDateTime() {
    updateDateTime();
    setInterval(updateDateTime, 1000);
    // Sync jadwal dari DB setiap 60 detik
    fetchScheduleConfig();
    setInterval(fetchScheduleConfig, 60 * 1000);
}

function isDisplayOn(nowMin, onMin, offMin) {
    if (onMin <= offMin) {
        // Normal: on=07:00, off=17:00 → ON saat onMin <= nowMin < offMin
        return nowMin >= onMin && nowMin < offMin;
    } else {
        // Overnight: on=17:09, off=17:00 → OFF hanya di celah kecil antara off–on
        // Contoh: OFF hanya 17:00–17:09, sisanya (17:09–16:59) ON
        return nowMin >= onMin || nowMin < offMin;
    }
}

function updateDateTime() {
    const now = new Date();
    const days   = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'];
    const months = ['Januari','Februari','Maret','April','Mei','Juni',
                    'Juli','Agustus','September','Oktober','November','Desember'];

    const h = String(now.getHours()).padStart(2,'0');
    const m = String(now.getMinutes()).padStart(2,'0');
    const colon = now.getSeconds() % 2 === 0 ? ':' : '<span style="opacity:.2">:</span>';

    const timeEl = document.getElementById('current-time');
    if (timeEl) timeEl.innerHTML = `${h}${colon}${m}`;

    const dayEl  = document.getElementById('current-day');
    const dateEl = document.getElementById('current-date');
    if (dayEl)  dayEl.textContent  = days[now.getDay()];
    if (dateEl) dateEl.textContent = months[now.getMonth()] + ' ' + String(now.getDate()).padStart(2,'0');

    // Cek standby tepat saat detik 0 (menit berganti) — hindari trigger berulang
    if (now.getSeconds() === 0) {
        const nowMin = now.getHours() * 60 + now.getMinutes();
        const [offH, offM] = SCHED_OFF.split(':').map(Number);
        const [onH,  onM]  = SCHED_ON.split(':').map(Number);
        const offMin = offH * 60 + offM;
        const onMin  = onH  * 60 + onM;

        if (!isDisplayOn(nowMin, onMin, offMin)) {
            console.log(`[Schedule] Masuk standby — now=${h}:${m} on=${SCHED_ON} off=${SCHED_OFF}`);
            window.location.href = '/';
        }
    }
}

/* ============================================================
   AGENDA AUTO SCROLL
   Uses requestAnimationFrame with stored handle (cancelable).
   dt is capped at 0.1s to prevent jump after tab switch.
   ============================================================ */
function initAgendaScroll() {
    const container = document.getElementById('agenda-list');
    const cards     = Array.from(container.querySelectorAll('.agenda-card'));
    if (cards.length === 0) return;

    const inner = document.createElement('div');
    inner.id = 'agenda-list-inner';
    cards.forEach(c => inner.appendChild(c));

    if (cards.length >= 2) {
        cards.forEach(c => {
            const clone = c.cloneNode(true);
            clone.classList.add('clone');
            inner.appendChild(clone);
        });
    }

    container.appendChild(inner);
    initAgendaClickHandlers();

    requestAnimationFrame(() => {
        const setHeight = cards.reduce((sum, c) => sum + c.offsetHeight + 9, 0);
        if (setHeight === 0) return;

        let pos    = 0;
        let last   = null;
        let paused = false;
        const speed = 18; // px/sec

        container.addEventListener('mouseenter', () => { paused = true;  });
        container.addEventListener('mouseleave',  () => { paused = false; });

        function step(ts) {
            if (last !== null && !paused) {
                const dt = Math.min((ts - last) / 1000, 0.1);
                pos += speed * dt;
                if (pos >= setHeight) pos -= setHeight;
                inner.style.transform = `translateY(-${pos}px)`;
            }
            last = ts;
            STATE._agendaRAF = requestAnimationFrame(step);
        }

        STATE._agendaRAF = requestAnimationFrame(step);
    });
}

/* ============================================================
   NEWS TICKER
   Kecepatan konstan 80px/detik tidak peduli jumlah berita.
   Durasi dihitung dari lebar total track setelah duplikasi.
   ============================================================ */
function initNewsScroll() {
    const track = document.getElementById('news-ticker');
    if (!track) return;
    const chips = Array.from(track.querySelectorAll('.news-chip'));
    if (chips.length === 0) return;

    // Duplikasi chip untuk seamless loop
    chips.forEach(chip => track.appendChild(chip.cloneNode(true)));

    // Hitung durasi setelah render selesai
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            // Lebar satu set chip (setengah dari total track karena sudah diduplikasi)
            const halfWidth = track.scrollWidth / 2;

            // Kecepatan konstan 80px/detik → durasi menyesuaikan jumlah berita
            const SPEED_PX_PER_SEC = 80;
            const duration = halfWidth / SPEED_PX_PER_SEC;

            // Set CSS variable untuk @keyframes translateX endpoint
            track.style.setProperty('--news-scroll-width', `-${halfWidth}px`);

            // Apply animation dengan durasi yang sudah dihitung
            track.style.animation = `scrollNews ${duration.toFixed(2)}s linear infinite`;

            console.log(`News ticker: ${chips.length} items, width=${halfWidth}px, duration=${duration.toFixed(1)}s`);
        });
    });
}

/* ============================================================
   AGENDA CLICK — manual media override
   ============================================================ */
function initAgendaClickHandlers() {
    document.querySelectorAll('.agenda-card:not(.clone)').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.agenda-card').forEach(c => c.classList.remove('active'));
            const id = card.dataset.id;
            document.querySelectorAll(`.agenda-card[data-id="${id}"]`).forEach(c => c.classList.add('active'));

            clearTimeout(STATE.templateTimer);
            clearTimeout(STATE.adTriggerTimer);
            stopProgress();

            displayManualMedia(card.dataset.mediaType, card.dataset.mediaPath);
        });
    });
}

function displayManualMedia(type, path) {
    const display = document.getElementById('media-display');
    safeCleanDisplay(display);

    if (type === 'photo' || type === 'image') {
        display.appendChild(buildImg('/' + path));
    } else if (type === 'video') {
        display.appendChild(buildVideo('/' + path, false));
    }
    hideBadge();
}

/* ============================================================
   TEMPLATE ROTATION
   Queue: [template1, template2, ..., ad1, ad2, ...] — lalu loop
   Ads masuk di main content (bukan popup) setelah semua template selesai
   ============================================================ */
function startTemplateRotation() {
    if (STATE.templates.length === 0 && STATE.ads.length === 0) {
        console.warn('No templates or ads available');
        return;
    }

    // ⑤ Gabungkan templates + ads jadi satu antrian
    // Template pakai field template_name, template_type, file_path, duration
    // Ad dikonversi ke format yang sama agar displayTemplate bisa handle
    const adItems = STATE.ads.map(ad => ({
        template_name: ad.ad_name,
        template_type: ad.ad_type,   // 'image' atau 'video'
        file_path:     ad.file_path,
        duration:      ad.duration || 10,
        _is_ad:        true,         // flag untuk badge label
    }));

    STATE.queue = [...STATE.templates, ...adItems];
    STATE.currentIndex = 0;

    console.log(`Queue: ${STATE.templates.length} template + ${adItems.length} ads = ${STATE.queue.length} total`);
    displayFromQueue(0);
}

function displayFromQueue(index) {
    if (STATE.advancing) return;
    if (STATE.queue.length === 0) return;

    // Loop kembali ke awal
    if (index >= STATE.queue.length) index = 0;

    STATE.currentIndex   = index;
    STATE.currentTemplateIndex = index; // compat dengan advanceTemplate
    STATE.advancing = false;

    const item    = STATE.queue[index];
    const display = document.getElementById('media-display');

    console.log(`[${index + 1}/${STATE.queue.length}] "${item.template_name}" [${item.template_type}]${item._is_ad ? ' 📢 AD' : ''}`);

    safeCleanDisplay(display);
    stopProgress();
    clearTimeout(STATE.templateTimer);

    // Badge: iklan ditandai "IKLAN"
    showBadge(item._is_ad ? `📢 ${item.template_name}` : item.template_name);

    if (item.template_type === 'image') {
        showImageTemplate(display, item, index);
    } else if (item.template_type === 'video') {
        showVideoTemplate(display, item, index);
    } else {
        STATE.templateTimer = setTimeout(() => advanceTemplate(index), 10000);
    }
}

function displayTemplate(index) {
    // Alias untuk kompatibilitas dengan kode lama (advanceTemplate, keyboard shortcut)
    displayFromQueue(index);
}

function showImageTemplate(display, item, index) {
    const img = buildImg('/' + item.file_path);
    display.appendChild(img);

    const dur = item.duration || 10;
    startProgress(dur);

    STATE.templateTimer = setTimeout(() => advanceTemplate(index), dur * 1000);
}

function showVideoTemplate(display, item, index) {
    const vid = buildVideo('/' + item.file_path, false);

    vid.addEventListener('ended', () => {
        advanceTemplate(index);
    });

    vid.addEventListener('error', () => {
        console.error('Video error, skipping in 3s');
        setTimeout(() => advanceTemplate(index), 3000);
    });

    display.appendChild(vid);

    vid.play()
        .then(() => {
            // Setelah gate, unmute aman
            vid.muted  = false;
            vid.volume = 1.0;
        })
        .catch(err => {
            // Jika masih blocked (mis. tidak ada gate), tetap lanjut muted
            console.warn('[Video] play() blocked:', err.message);
        });

    // play() explicit — lebih reliable dari autoplay attribute di Raspberry Pi
    // vid.play()
    //     .then(() => {
    //         // .then() = browser sudah commit play, aman untuk unmute
    //         // Ini satu-satunya tempat yang benar untuk unmute:
    //         // - Bukan di 'playing' event  → bisa trigger policy re-evaluation
    //         // - Bukan di 'volumechange'   → infinite loop
    //         // - Bukan sebelum play()      → autoplay langsung diblokir
    //         vid.muted  = false;
    //         vid.volume = 1.0;
    //     })
    //     .catch(err => {
    //         // Autoplay masih diblokir (policy strict / flag belum dipasang)
    //         console.warn('[Video] play() blocked:', err.message);
    //         console.warn('[Video] Pastikan Chromium flag sudah dipasang:');
    //         console.warn('[Video] --autoplay-policy=no-user-gesture-required');
    //         // Video tetap berjalan (muted), tidak perlu fallback lain
    //     });
}

function advanceTemplate(fromIndex) {
    if (STATE.advancing) return;
    if (STATE.currentIndex !== fromIndex) return;
    STATE.advancing = true;

    clearTimeout(STATE.templateTimer);
    stopProgress();

    setTimeout(() => {
        STATE.advancing = false;
        displayFromQueue(fromIndex + 1);
    }, 80);
}

/* ============================================================
   SAFE DISPLAY CLEANUP
   Most important function for preventing crashes.
   Video decoders must be explicitly released by:
     1. pause()
     2. removeAttribute('src')
     3. load()  — triggers abort of network + frees GPU decoder
   ============================================================ */
function safeCleanDisplay(display) {
    const mediaEls = display.querySelectorAll('.media-el');
    mediaEls.forEach(el => {
        if (el.tagName === 'VIDEO') {
            try {
                el.pause();
                el.removeAttribute('src');
                el.load();
            } catch(e) { /* ignore */ }
        }
        el.remove();
    });
    // Bersihkan flag video-playing saat media diganti
    document.body.classList.remove('video-playing');

    const placeholder = display.querySelector('.media-placeholder');
    if (placeholder) placeholder.remove();
}

/* ============================================================
   MEDIA BUILDERS
   ============================================================ */
function buildImg(src) {
    const img = document.createElement('img');
    img.src = src;
    img.className = 'media-el';
    img.onerror = () => { img.style.display = 'none'; };
    return img;
}

function buildVideo(src, loop = false) {
    const vid = document.createElement('video');
    vid.src         = src;
    vid.className   = 'media-el';
    vid.dataset.type = 'video';
    vid.muted       = true;     // mulai muted agar autoplay tidak diblokir
    vid.loop        = loop;
    vid.playsInline = true;
    vid.preload     = 'auto';
    vid.volume      = 1.0;

    vid.setAttribute('x-webkit-airplay', 'allow');
    vid.setAttribute('webkit-playsinline', '');
    vid.controls               = false;
    vid.disablePictureInPicture = true;

    vid.addEventListener('playing', () => {
        document.body.classList.add('video-playing');
    });
    vid.addEventListener('pause', () => {
        document.body.classList.remove('video-playing');
    });
    vid.addEventListener('ended', () => {
        document.body.classList.remove('video-playing');
    });

    return vid;
}

/* ============================================================
   PROGRESS BAR (images only)
   ============================================================ */
function startProgress(durationSec) {
    const wrap = document.getElementById('media-progress');
    const bar  = document.getElementById('media-progress-bar');
    if (!wrap || !bar) return;

    bar.style.transition = 'none';
    bar.style.width = '0%';
    wrap.classList.add('visible');

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            bar.style.transition = `width ${durationSec}s linear`;
            bar.style.width = '100%';
        });
    });
}

function stopProgress() {
    const wrap = document.getElementById('media-progress');
    const bar  = document.getElementById('media-progress-bar');
    if (!wrap || !bar) return;
    wrap.classList.remove('visible');
    bar.style.transition = 'none';
    bar.style.width = '0%';
}

/* ============================================================
   TEMPLATE BADGE
   ============================================================ */
function showBadge(name) {
    const badge = document.getElementById('template-badge');
    const text  = document.getElementById('template-badge-text');
    if (!badge || !text) return;
    text.textContent = name || '—';
    badge.classList.add('show');
    clearTimeout(STATE._badgeTimer);
    STATE._badgeTimer = setTimeout(() => badge.classList.remove('show'), 3500);
}

function hideBadge() {
    document.getElementById('template-badge')?.classList.remove('show');
}

/* ============================================================
   ADVERTISEMENT POPUP
   ⚠ DINONAKTIFKAN — iklan sekarang masuk di antrian main content (queue).
   Kode tetap ada untuk re-aktivasi nanti jika dibutuhkan.
   ============================================================ */
function scheduleAd(/* templateDurationSec */) {
    // Ad popup disabled — ads are now in the main content queue
}

function showAd(ad) {
    // Ad popup disabled
    console.log(`[AD POPUP DISABLED] ${ad?.ad_name}`);
}

function closeAd() {
    // Ad popup disabled
}

function initAdHandlers() {
    // Ad popup disabled — close button no longer exists in DOM
    // document.getElementById('ad-close')?.addEventListener('click', closeAd);
}

/*
// ── ORIGINAL POPUP CODE (uncomment to re-enable) ───────────────────────────
function scheduleAd(templateDurationSec) {
    clearTimeout(STATE.adTriggerTimer);
    if (STATE.ads.length === 0) return;

    const ad = STATE.ads[STATE.currentAdIndex];
    let delay;

    if (templateDurationSec == null) {
        delay = (ad.trigger_time || 10) * 1000;
    } else {
        const showAt = templateDurationSec - (ad.trigger_time || 8);
        delay = Math.max(0, showAt) * 1000;
    }

    STATE.adTriggerTimer = setTimeout(() => showAd(ad), delay);
}

function showAd(ad) {
    const popup   = document.getElementById('ad-popup');
    const content = document.getElementById('ad-content');
    const cdEl    = document.getElementById('ad-countdown');

    const oldVid = content.querySelector('video');
    if (oldVid) {
        try { oldVid.pause(); oldVid.removeAttribute('src'); oldVid.load(); } catch(e){}
    }
    content.innerHTML = '';

    if (ad.ad_type === 'image') {
        content.appendChild(buildImg('/' + ad.file_path));
    } else if (ad.ad_type === 'video') {
        content.appendChild(buildVideo('/' + ad.file_path, false));
    }

    popup.classList.remove('hidden');

    const dur = ad.duration || 10;
    let remaining = dur;
    if (cdEl) cdEl.textContent = `${remaining}s`;

    clearInterval(STATE._adCdInterval);
    STATE._adCdInterval = setInterval(() => {
        remaining--;
        if (cdEl) cdEl.textContent = `${remaining}s`;
        if (remaining <= 0) clearInterval(STATE._adCdInterval);
    }, 1000);

    clearTimeout(STATE.adTimer);
    STATE.adTimer = setTimeout(() => closeAd(), dur * 1000);

    STATE.currentAdIndex = (STATE.currentAdIndex + 1) % STATE.ads.length;
}

function closeAd() {
    const popup   = document.getElementById('ad-popup');
    const content = document.getElementById('ad-content');

    const vid = content.querySelector('video');
    if (vid) {
        try { vid.pause(); vid.removeAttribute('src'); vid.load(); } catch(e){}
    }

    popup.classList.add('hidden');
    clearTimeout(STATE.adTimer);
    clearInterval(STATE._adCdInterval);
}

function initAdHandlers() {
    document.getElementById('ad-close')?.addEventListener('click', closeAd);
}
// ────────────────────────────────────────────────────────────────────────────
*/

/* ============================================================
   FLOATING MENU
   ============================================================ */
function initFloatingMenu() {
    const btn     = document.getElementById('menu-button');
    const menu    = document.getElementById('floating-menu');
    const overlay = document.getElementById('menu-overlay');

    btn?.addEventListener('click', () => {
        menu.classList.toggle('active');
        overlay.classList.toggle('active');
    });

    overlay?.addEventListener('click', () => {
        menu.classList.remove('active');
        overlay.classList.remove('active');
    });
}

/* ============================================================
   PAGE VISIBILITY API
   Free GPU decoder when tab is backgrounded
   ============================================================ */
document.addEventListener('visibilitychange', () => {
    const vids = document.querySelectorAll('.media-el');
    if (document.hidden) {
        vids.forEach(v => { if (v.tagName === 'VIDEO') { try { v.pause(); } catch(e){} } });
    } else {
        vids.forEach(v => { if (v.tagName === 'VIDEO') { try { v.play(); } catch(e){} } });
    }
});

/* ============================================================
   KEYBOARD SHORTCUTS
   ============================================================ */
document.addEventListener('keydown', e => {
    switch(e.key) {
        case 'n': advanceTemplate(STATE.currentTemplateIndex); break;
        case 'a': if (STATE.ads.length) showAd(STATE.ads[STATE.currentAdIndex]); break;
        case 'r': location.reload(); break;
    }
});