/* ============================================================
   DIGITAL SIGNAGE — script.js
   Smart video duration: rotates on 'ended', not fixed timer.
   Images use configured duration with animated progress bar.
   ============================================================ */

'use strict';

const STATE = {
    templates: window.SIGNAGE_DATA?.templates || [],
    ads:       window.SIGNAGE_DATA?.advertisements || [],
    agendas:   window.SIGNAGE_DATA?.agendas || [],

    currentTemplateIndex: 0,
    currentAdIndex: 0,

    templateTimer:  null,   // for image auto-advance
    adTimer:        null,
    adTriggerTimer: null,
    progressTimer:  null,

    // prevent double-advance when video ends near scheduled timer
    advancing: false,
};

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Digital Signage v2 initialized');
    console.log('Templates:', STATE.templates.length);
    console.log('Ads:', STATE.ads.length);

    initDateTime();
    initAgendaScroll();
    initNewsScroll();
    initAgendaClickHandlers();
    initFloatingMenu();
    initAdHandlers();
    startTemplateRotation();
});

/* ============================================================
   DATE / TIME
   ============================================================ */
function initDateTime() {
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

function updateDateTime() {
    const now = new Date();
    const days   = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'];
    const months = ['Januari','Februari','Maret','April','Mei','Juni',
                    'Juli','Agustus','September','Oktober','November','Desember'];

    const h = String(now.getHours()).padStart(2,'0');
    const m = String(now.getMinutes()).padStart(2,'0');
    // blinking colon
    const colon = now.getSeconds() % 2 === 0 ? ':' : '<span style="opacity:.2">:</span>';

    const timeEl = document.getElementById('current-time');
    if (timeEl) timeEl.innerHTML = `${h}${colon}${m}`;

    const dayEl  = document.getElementById('current-day');
    const dateEl = document.getElementById('current-date');
    if (dayEl)  dayEl.textContent  = days[now.getDay()];
    if (dateEl) dateEl.textContent = months[now.getMonth()] + ' ' + String(now.getDate()).padStart(2,'0');
}

/* ============================================================
   AGENDA AUTO SCROLL
   ============================================================ */
function initAgendaScroll() {
    const container = document.getElementById('agenda-list');
    const cards     = Array.from(container.querySelectorAll('.agenda-card'));

    if (cards.length === 0) return;

    // Create inner wrapper
    const inner = document.createElement('div');
    inner.id = 'agenda-list-inner';

    // Move existing cards in
    cards.forEach(c => inner.appendChild(c));

    // Duplicate if needed for infinite scroll
    if (cards.length >= 2) {
        cards.forEach(c => {
            const clone = c.cloneNode(true);
            clone.classList.add('clone');
            inner.appendChild(clone);
        });
    }

    container.appendChild(inner);
    initAgendaClickHandlers();

    // Measure one-set height then animate
    requestAnimationFrame(() => {
        const setHeight = cards.reduce((sum, c) => sum + c.offsetHeight + 9, 0);
        if (setHeight === 0) return;

        let pos = 0;
        const speed = 18; // px per second
        let last = null;
        let paused = false;

        container.addEventListener('mouseenter', () => paused = true);
        container.addEventListener('mouseleave',  () => paused = false);

        function step(ts) {
            if (!last) last = ts;
            const dt = (ts - last) / 1000;
            last = ts;

            if (!paused) {
                pos += speed * dt;
                if (pos >= setHeight) pos -= setHeight;
                inner.style.transform = `translateY(-${pos}px)`;
            }
            requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    });
}

/* ============================================================
   NEWS TICKER DUPLICATE
   ============================================================ */
function initNewsScroll() {
    const track = document.getElementById('news-ticker');
    if (!track) return;
    const chips = Array.from(track.querySelectorAll('.news-chip'));
    if (chips.length === 0) return;

    // Duplicate for seamless loop
    chips.forEach(chip => {
        const clone = chip.cloneNode(true);
        track.appendChild(clone);
    });
}

/* ============================================================
   AGENDA CLICK — manual media override
   ============================================================ */
function initAgendaClickHandlers() {
    document.querySelectorAll('.agenda-card:not(.clone)').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.agenda-card').forEach(c => c.classList.remove('active'));
            // activate all copies (original + clone)
            const id = card.dataset.id;
            document.querySelectorAll(`.agenda-card[data-id="${id}"]`).forEach(c => c.classList.add('active'));

            // Pause rotation, show agenda media
            clearTimeout(STATE.templateTimer);
            clearTimeout(STATE.adTriggerTimer);
            stopProgress();

            displayManualMedia(card.dataset.mediaType, card.dataset.mediaPath);
        });
    });
}

function displayManualMedia(type, path) {
    const display = document.getElementById('media-display');
    clearDisplay(display);

    if (type === 'photo' || type === 'image') {
        const img = buildImg('/' + path);
        display.appendChild(img);
    } else if (type === 'video') {
        const vid = buildVideo('/' + path, false); // not looping for manual
        display.appendChild(vid);
    }
    hideBadge();
}

/* ============================================================
   TEMPLATE ROTATION
   ============================================================ */
function startTemplateRotation() {
    if (STATE.templates.length === 0) {
        console.warn('⚠️  No templates');
        return;
    }
    displayTemplate(0);
}

function displayTemplate(index) {
    if (STATE.advancing) return;
    if (index >= STATE.templates.length) index = 0;

    STATE.currentTemplateIndex = index;
    STATE.advancing = false;

    const tpl     = STATE.templates[index];
    const display = document.getElementById('media-display');

    console.log(`📺 Template ${index + 1}/${STATE.templates.length}: "${tpl.template_name}" [${tpl.template_type}]`);

    clearDisplay(display);
    stopProgress();
    clearTimeout(STATE.templateTimer);

    showBadge(tpl.template_name);

    if (tpl.template_type === 'image') {
        showImageTemplate(display, tpl, index);
    } else if (tpl.template_type === 'video') {
        showVideoTemplate(display, tpl, index);
    } else {
        // unknown type — advance after fallback duration
        scheduleNextTemplate(index, tpl.duration || 10);
    }

    scheduleAd(tpl.template_type === 'video' ? null : tpl.duration);
}

/* --- Image Template --- */
function showImageTemplate(display, tpl, index) {
    const img = buildImg('/' + tpl.file_path);
    display.appendChild(img);

    const dur = tpl.duration || 10;
    startProgress(dur);

    STATE.templateTimer = setTimeout(() => {
        advanceTemplate(index);
    }, dur * 1000);
}

/* --- Video Template --- */
function showVideoTemplate(display, tpl, index) {
    const vid = buildVideo('/' + tpl.file_path, false);

    // When video ends naturally → advance
    vid.addEventListener('ended', () => {
        console.log('🎬 Video ended, advancing');
        advanceTemplate(index);
    });

    // Error fallback
    vid.addEventListener('error', () => {
        console.error('❌ Video error, skipping in 3s');
        setTimeout(() => advanceTemplate(index), 3000);
    });

    display.appendChild(vid);
    // No timer — duration comes from video itself
}

/* --- Advance helper (debounced) --- */
function advanceTemplate(fromIndex) {
    if (STATE.advancing) return;
    if (STATE.currentTemplateIndex !== fromIndex) return; // stale call
    STATE.advancing = true;

    clearTimeout(STATE.templateTimer);
    stopProgress();

    setTimeout(() => {
        STATE.advancing = false;
        displayTemplate(fromIndex + 1);
    }, 50);
}

/* ============================================================
   MEDIA ELEMENT BUILDERS
   ============================================================ */
function buildImg(src) {
    const img = document.createElement('img');
    img.src = src;
    img.className = 'media-el';
    img.onerror = () => { img.src = '/static/uploads/placeholder.jpg'; };
    return img;
}

function buildVideo(src, loop = true) {
    const vid = document.createElement('video');
    vid.src  = src;
    vid.className = 'media-el';
    vid.autoplay  = true;
    vid.muted     = true;
    vid.loop      = loop;
    vid.playsInline = true;
    return vid;
}

/* ============================================================
   CLEAR DISPLAY
   ============================================================ */
function clearDisplay(display) {
    // Remove all media elements (keep progress bar and badge)
    Array.from(display.children).forEach(child => {
        if (child.classList.contains('media-el') || child.classList.contains('media-placeholder')) {
            child.remove();
        }
    });

    // If display is now empty of media, show nothing (progress/badge stay)
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

    clearTimeout(STATE.progressTimer);

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
   ADVERTISEMENT
   ============================================================ */
function scheduleAd(templateDurationSec) {
    clearTimeout(STATE.adTriggerTimer);
    if (STATE.ads.length === 0) return;

    const ad = STATE.ads[STATE.currentAdIndex];

    let delay;
    if (templateDurationSec == null) {
        // Video — show ad after trigger_time seconds
        delay = (ad.trigger_time || 10) * 1000;
    } else {
        // Image — show ad before template ends
        const showAt = templateDurationSec - (ad.trigger_time || 8);
        delay = Math.max(0, showAt) * 1000;
    }

    console.log(`📢 Ad "${ad.ad_name}" scheduled in ${(delay/1000).toFixed(1)}s`);

    STATE.adTriggerTimer = setTimeout(() => {
        showAd(ad);
    }, delay);
}

function showAd(ad) {
    console.log(`📢 Showing AD: ${ad.ad_name}`);
    const popup   = document.getElementById('ad-popup');
    const content = document.getElementById('ad-content');
    const cdEl    = document.getElementById('ad-countdown');

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
    STATE.adTimer = setTimeout(() => {
        popup.classList.add('hidden');
        clearInterval(STATE._adCdInterval);
    }, dur * 1000);

    STATE.currentAdIndex = (STATE.currentAdIndex + 1) % STATE.ads.length;
}

function initAdHandlers() {
    document.getElementById('ad-close')?.addEventListener('click', () => {
        document.getElementById('ad-popup').classList.add('hidden');
        clearTimeout(STATE.adTimer);
        clearInterval(STATE._adCdInterval);
    });
}

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
   KEYBOARD SHORTCUTS
   ============================================================ */
document.addEventListener('keydown', e => {
    switch(e.key) {
        case 'n': advanceTemplate(STATE.currentTemplateIndex); break;
        case 'a': if (STATE.ads.length) showAd(STATE.ads[STATE.currentAdIndex]); break;
        case 'r': location.reload(); break;
    }
});