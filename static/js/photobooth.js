// Camera and capture functionality
let videoStream = null;
let capturedImageData = null;

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const preview = document.getElementById('preview');
const previewImage = document.getElementById('preview-image');
const captureBtn = document.getElementById('capture-btn');
const retakeBtn = document.getElementById('retake-btn');
const saveBtn = document.getElementById('save-btn');
const previewControls = document.getElementById('preview-controls');
const countdown = document.getElementById('countdown');
const countdownNumber = document.getElementById('countdown-number');
const flash = document.getElementById('flash');
const statusMessage = document.getElementById('status-message');

// Initialize camera
async function initCamera() {
    try {
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 960 },
                facingMode: 'user'
            },
            audio: false
        };
        
        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = videoStream;
        
        showStatus('Kamera siap!', 'success');
        setTimeout(() => hideStatus(), 2000);
    } catch (error) {
        console.error('Error accessing camera:', error);
        showStatus('Tidak dapat mengakses kamera. Pastikan izin kamera diaktifkan.', 'error');
    }
}

// Countdown before capture
function startCountdown() {
    return new Promise((resolve) => {
        let count = 3;
        countdownNumber.textContent = count;
        countdown.style.display = 'flex';
        
        const countInterval = setInterval(() => {
            count--;
            if (count > 0) {
                countdownNumber.textContent = count;
                // Reset animation
                countdownNumber.style.animation = 'none';
                setTimeout(() => {
                    countdownNumber.style.animation = 'pulse 1s ease-in-out';
                }, 10);
            } else {
                clearInterval(countInterval);
                countdown.style.display = 'none';
                resolve();
            }
        }, 1000);
    });
}

// Capture photo
async function capturePhoto() {
    captureBtn.disabled = true;
    
    // Start countdown
    await startCountdown();
    
    // Flash effect
    flash.classList.add('active');
    setTimeout(() => {
        flash.classList.remove('active');
    }, 500);
    
    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw current video frame to canvas
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get image data
    capturedImageData = canvas.toDataURL('image/png');
    
    // Show preview
    previewImage.src = capturedImageData;
    video.style.display = 'none';
    preview.style.display = 'block';
    
    // Show preview controls
    captureBtn.style.display = 'none';
    previewControls.style.display = 'flex';
    
    captureBtn.disabled = false;
}

// Retake photo
function retakePhoto() {
    video.style.display = 'block';
    preview.style.display = 'none';
    captureBtn.style.display = 'flex';
    previewControls.style.display = 'none';
    capturedImageData = null;
}

// Save photo
async function savePhoto() {
    if (!capturedImageData) {
        showStatus('Tidak ada foto untuk disimpan', 'error');
        return;
    }
    
    saveBtn.disabled = true;
    showStatus('Menyimpan foto...', 'success');
    
    try {
        const response = await fetch('/api/capture', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: capturedImageData
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStatus('Foto berhasil disimpan!', 'success');
            
            // Add to gallery
            addPhotoToGallery(capturedImageData);
            
            // Reset after 2 seconds
            setTimeout(() => {
                retakePhoto();
                hideStatus();
            }, 2000);
        } else {
            showStatus('Gagal menyimpan foto: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error saving photo:', error);
        showStatus('Terjadi kesalahan saat menyimpan foto', 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

// Add photo to gallery
function addPhotoToGallery(imageData) {
    const gallery = document.getElementById('gallery');
    
    const galleryItem = document.createElement('div');
    galleryItem.className = 'gallery-item';
    
    const img = document.createElement('img');
    img.src = imageData;
    img.alt = 'Captured photo';
    
    galleryItem.appendChild(img);
    gallery.insertBefore(galleryItem, gallery.firstChild);
    
    // Keep only last 12 photos in gallery
    while (gallery.children.length > 12) {
        gallery.removeChild(gallery.lastChild);
    }
}

// Load recent photos
async function loadRecentPhotos() {
    // This would typically fetch from the server
    // For now, we'll just show a placeholder message
    const gallery = document.getElementById('gallery');
    
    if (gallery.children.length === 0) {
        const placeholder = document.createElement('div');
        placeholder.style.gridColumn = '1 / -1';
        placeholder.style.textAlign = 'center';
        placeholder.style.padding = '40px';
        placeholder.style.color = '#999';
        placeholder.innerHTML = '<p style="font-size: 18px;">Belum ada foto yang diambil</p>';
        gallery.appendChild(placeholder);
    }
}

// Show status message
function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
}

// Hide status message
function hideStatus() {
    statusMessage.style.display = 'none';
}

// Event listeners
captureBtn.addEventListener('click', capturePhoto);
retakeBtn.addEventListener('click', retakePhoto);
saveBtn.addEventListener('click', savePhoto);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initCamera();
    loadRecentPhotos();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
});
