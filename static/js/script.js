/* ============================================================
   DIGITAL SIGNAGE — script.js  v3 (memory-safe)
   - Video elements properly paused + src cleared before removal
   - RAF agenda loop uses cancelAnimationFrame handle
   - All timers/intervals tracked and cleared
   - No DOM node accumulation
   - Page Visibility API: pause video when tab hidden
   ============================================================ */

'use strict';

const STATE = {
    templates: window.SIGNAGE_DATA?.templates || [],
    ads:       window.SIGNAGE_DATA?.advertisements || [],
    agendas:   window.SIGNAGE_DATA?.agendas || [],

    currentTemplateIndex: 0,
    currentAdIndex: 0,

    templateTimer:  null,
    adTimer:        null,
    adTriggerTimer: null,
    _badgeTimer:    null,
    _adCdInterval:  null,
    _agendaRAF:     null,   // cancelAnimationFrame handle

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
   NEWS TICKER — duplicate chips for seamless loop
   ============================================================ */
function initNewsScroll() {
    const track = document.getElementById('news-ticker');
    if (!track) return;
    const chips = Array.from(track.querySelectorAll('.news-chip'));
    if (chips.length === 0) return;
    chips.forEach(chip => track.appendChild(chip.cloneNode(true)));
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
   ============================================================ */
function startTemplateRotation() {
    if (STATE.templates.length === 0) {
        console.warn('No templates available');
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

    console.log(`Template ${index + 1}/${STATE.templates.length}: "${tpl.template_name}" [${tpl.template_type}]`);

    // CRITICAL: destroy previous media elements properly
    safeCleanDisplay(display);
    stopProgress();
    clearTimeout(STATE.templateTimer);

    showBadge(tpl.template_name);

    if (tpl.template_type === 'image') {
        showImageTemplate(display, tpl, index);
    } else if (tpl.template_type === 'video') {
        showVideoTemplate(display, tpl, index);
    } else {
        // unknown — fallback after 10s
        STATE.templateTimer = setTimeout(() => advanceTemplate(index), 10000);
    }

    scheduleAd(tpl.template_type === 'video' ? null : tpl.duration);
}

function showImageTemplate(display, tpl, index) {
    const img = buildImg('/' + tpl.file_path);
    display.appendChild(img);

    const dur = tpl.duration || 10;
    startProgress(dur);

    STATE.templateTimer = setTimeout(() => advanceTemplate(index), dur * 1000);
}

function showVideoTemplate(display, tpl, index) {
    const vid = buildVideo('/' + tpl.file_path, false);

    vid.addEventListener('ended', () => {
        console.log('Video ended, advancing');
        advanceTemplate(index);
    });

    vid.addEventListener('error', () => {
        console.error('Video load error, skipping in 3s');
        setTimeout(() => advanceTemplate(index), 3000);
    });

    display.appendChild(vid);
    // No setTimeout — duration driven by video's natural end
}

function advanceTemplate(fromIndex) {
    if (STATE.advancing) return;
    if (STATE.currentTemplateIndex !== fromIndex) return;
    STATE.advancing = true;

    clearTimeout(STATE.templateTimer);
    stopProgress();

    setTimeout(() => {
        STATE.advancing = false;
        displayTemplate(fromIndex + 1);
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
    img.onerror = () => { img.src = '/static/uploads/placeholder.jpg'; };
    return img;
}

function buildVideo(src, loop = false) {
    const vid = document.createElement('video');
    vid.src         = src;
    vid.className   = 'media-el';
    vid.autoplay    = true;
    vid.muted       = true;
    vid.loop        = loop;
    vid.playsInline = true;
    vid.preload     = 'auto';
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
   ADVERTISEMENT
   ============================================================ */
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
    console.log(`AD: ${ad.ad_name}`);
    const popup   = document.getElementById('ad-popup');
    const content = document.getElementById('ad-content');
    const cdEl    = document.getElementById('ad-countdown');

    // Release previous ad video
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

    // Release video decoder
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