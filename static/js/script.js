const STATE = {
    templates: window.SIGNAGE_DATA?.templates || [],
    ads: window.SIGNAGE_DATA?.advertisements || [],
    agendas: window.SIGNAGE_DATA?.agendas || [],
    currentTemplateIndex: 0,
    currentAdIndex: 0,
    templateTimer: null,
    adTimer: null,
    adTriggerTimer: null,
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Digital Signage initialized');
    console.log('Templates:', STATE.templates);
    console.log('Ads:', STATE.ads);
    
    initDateTime();
    initAgendaAutoScroll();
    initNewsAutoScroll();
    initAgendaClickHandlers();
    initFloatingMenu();
    initAdvertisementHandlers();
    startTemplateRotation();
});

function initDateTime() {
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

function updateDateTime() {
    const now = new Date();
    const days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
    const months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
    
    document.getElementById('current-time').textContent = 
        now.getHours().toString().padStart(2, '0') + ':' + 
        now.getMinutes().toString().padStart(2, '0');
    
    document.getElementById('current-day').textContent = days[now.getDay()];
    document.getElementById('current-date').textContent = 
        months[now.getMonth()] + ' ' + now.getDate().toString().padStart(2, '0');
}

function initAgendaAutoScroll() {
    const agendaList = document.getElementById('agenda-list');
    const items = agendaList.querySelectorAll('.agenda-item');
    
    if (items.length > 3) {
        items.forEach(item => {
            const clone = item.cloneNode(true);
            agendaList.appendChild(clone);
        });
        
        const wrapper = document.createElement('div');
        wrapper.className = 'agenda-list-wrapper';
        while (agendaList.firstChild) {
            wrapper.appendChild(agendaList.firstChild);
        }
        agendaList.appendChild(wrapper);
        
        initAgendaClickHandlers();
    }
}

function initNewsAutoScroll() {
    const newsTicker = document.getElementById('news-ticker');
    const items = newsTicker.querySelectorAll('.news-item');
    
    items.forEach(item => {
        const clone = item.cloneNode(true);
        newsTicker.appendChild(clone);
    });
}

function initAgendaClickHandlers() {
    document.querySelectorAll('.agenda-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.agenda-item').forEach(a => a.classList.remove('active'));
            item.classList.add('active');
            
            const mediaType = item.dataset.mediaType;
            const mediaPath = item.dataset.mediaPath;
            displayAgendaMedia(mediaType, mediaPath);
        });
    });
}

function displayAgendaMedia(type, path) {
    console.log('📺 Display agenda:', type, path);
    
    const display = document.getElementById('media-display');
    display.innerHTML = '';
    
    if (type === 'photo') {
        const img = document.createElement('img');
        img.src = '/' + path;
        img.className = 'media-content image';
        img.onerror = function() {
            console.error('Failed to load:', path);
            this.src = '/static/uploads/placeholder.jpg';
        };
        img.onload = function() {
            console.log('✅ Image loaded successfully');
        };
        display.appendChild(img);
    } else if (type === 'video') {
        const video = document.createElement('video');
        video.src = '/' + path;
        video.className = 'media-content video';
        video.autoplay = true;
        video.muted = true;
        video.loop = true;
        display.appendChild(video);
    }
}

function startTemplateRotation() {
    if (STATE.templates.length === 0) {
        console.warn('⚠️ No templates available');
        return;
    }
    displayTemplate(0);
}

function displayTemplate(index) {
    if (index >= STATE.templates.length) index = 0;
    
    const template = STATE.templates[index];
    STATE.currentTemplateIndex = index;
    
    console.log(`📺 Template ${index + 1}/${STATE.templates.length}: ${template.template_name}`);
    
    const display = document.getElementById('media-display');
    display.innerHTML = '';
    
    if (template.template_type === 'image') {
        const img = document.createElement('img');
        img.src = '/' + template.file_path;
        img.className = 'media-content image';
        img.onload = () => console.log('✅ Template image loaded');
        img.onerror = () => console.error('❌ Failed to load template image');
        display.appendChild(img);
    } else if (template.template_type === 'video') {
        const video = document.createElement('video');
        video.src = '/' + template.file_path;
        video.className = 'media-content video';
        video.autoplay = true;
        video.muted = true;
        video.loop = true;
        display.appendChild(video);
    }
    
    scheduleAdvertisement(template.duration);
    
    clearTimeout(STATE.templateTimer);
    STATE.templateTimer = setTimeout(() => {
        displayTemplate(index + 1);
    }, template.duration * 1000);
}

function scheduleAdvertisement(templateDuration) {
    clearTimeout(STATE.adTriggerTimer);
    
    if (STATE.ads.length === 0) {
        console.log('⚠️ No ads');
        return;
    }
    
    const ad = STATE.ads[STATE.currentAdIndex];
    const showAt = (templateDuration - (ad.trigger_time || 10)) * 1000;
    
    console.log(`📢 Ad in ${showAt/1000}s`);
    
    STATE.adTriggerTimer = setTimeout(() => {
        showAdvertisement(ad);
    }, Math.max(0, showAt));
}

function showAdvertisement(ad) {
    console.log(`📢 AD: ${ad.ad_name}`);
    
    const popup = document.getElementById('ad-popup');
    const content = document.getElementById('ad-content');
    
    content.innerHTML = '';
    
    if (ad.ad_type === 'image') {
        const img = document.createElement('img');
        img.src = '/' + ad.file_path;
        content.appendChild(img);
    } else if (ad.ad_type === 'video') {
        const video = document.createElement('video');
        video.src = '/' + ad.file_path;
        video.autoplay = true;
        video.muted = true;
        content.appendChild(video);
    }
    
    popup.classList.remove('hidden');
    
    clearTimeout(STATE.adTimer);
    STATE.adTimer = setTimeout(() => {
        popup.classList.add('hidden');
    }, (ad.duration || 10) * 1000);
    
    STATE.currentAdIndex = (STATE.currentAdIndex + 1) % STATE.ads.length;
}

function initAdvertisementHandlers() {
    const closeBtn = document.getElementById('ad-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('ad-popup').classList.add('hidden');
            clearTimeout(STATE.adTimer);
        });
    }
}

function initFloatingMenu() {
    const menuBtn = document.getElementById('menu-button');
    const menu = document.getElementById('floating-menu');
    const overlay = document.getElementById('menu-overlay');
    
    menuBtn.addEventListener('click', () => {
        menu.classList.toggle('active');
        overlay.classList.toggle('active');
    });
    
    overlay.addEventListener('click', () => {
        menu.classList.remove('active');
        overlay.classList.remove('active');
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'n') displayTemplate(STATE.currentTemplateIndex + 1);
    if (e.key === 'a' && STATE.ads.length > 0) showAdvertisement(STATE.ads[STATE.currentAdIndex]);
    if (e.key === 'r') location.reload();
});