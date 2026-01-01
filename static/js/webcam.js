document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const captureBtn = document.getElementById('capture-btn');
    const statusMessage = document.getElementById('status-message');

    let stream = null;

    // Check if browser supports mediaDevices
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        statusMessage.textContent = 'Camera API not supported';
        statusMessage.className = 'text-danger';
        return;
    }

    startCamera();

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            video.play();
            statusMessage.textContent = 'Camera active. Ready to capture.';
        } catch (err) {
            console.error("Error accessing camera: ", err);
            statusMessage.textContent = 'Camera access denied. Please allow permission.';
            statusMessage.className = 'text-danger';
            captureBtn.disabled = true;
        }
    }

    captureBtn.addEventListener('click', async () => {
        if (!stream) return;

        // Visual feedback
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        // Set canvas dimensions
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw frame
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert to blob
        canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('face_image', blob, 'register.jpg');
            
            try {
                const response = await fetch('/capture_face', {
                    method: 'POST',
                    body: formData,
                    redirect: 'follow',
                    cache: 'no-store' // Prevent service worker caching issues
                });
                
                // Check for redirects
                if (response.redirected || response.status === 302 || response.status === 301) {
                    const redirectUrl = response.url || response.headers.get('Location');
                    if (redirectUrl) {
                        window.location.href = redirectUrl;
                        return;
                    }
                }
                
                // Fallback if not redirected (e.g. error but stay on page)
                // Reload to show flash messages
                window.location.reload();
                
            } catch (err) {
                console.error('Error sending frame:', err);
                statusMessage.textContent = 'Error uploading image.';
                statusMessage.className = 'text-danger';
                captureBtn.disabled = false;
                captureBtn.innerHTML = '<i class="fas fa-camera me-2"></i>Capture & Register';
            }
        }, 'image/jpeg');
    });
});
