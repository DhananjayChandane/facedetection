document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('overlay');
    const statusEl = document.getElementById('status');
    const messageEl = document.getElementById('message');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const captureBtn = document.getElementById('capture-btn');
    const attendanceList = document.getElementById('attendance-list');
    
    let stream = null;
    let geo = { lat: null, lng: null };
    let selectedDeviceId = null;
    const cameraSelect = document.getElementById('camera-select');
    
    async function getGeo() {
        if (!navigator.geolocation) return;
        try {
            await new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        geo.lat = pos.coords.latitude;
                        geo.lng = pos.coords.longitude;
                        resolve();
                    },
                    () => resolve(),
                    { enableHighAccuracy: true, timeout: 3000 }
                );
            });
        } catch (_) {}
    }
    
    async function listCameras() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
        const devices = await navigator.mediaDevices.enumerateDevices();
        const cams = devices.filter(d => d.kind === 'videoinput');
        if (cameraSelect) {
            cameraSelect.innerHTML = '';
            cams.forEach((cam, idx) => {
                const opt = document.createElement('option');
                opt.value = cam.deviceId;
                opt.textContent = cam.label || `Camera ${idx + 1}`;
                cameraSelect.appendChild(opt);
            });
            const saved = localStorage.getItem('preferredCameraId');
            if (saved && cams.some(c => c.deviceId === saved)) {
                selectedDeviceId = saved;
                cameraSelect.value = saved;
            } else if (cams.length > 0) {
                selectedDeviceId = cams[0].deviceId;
                cameraSelect.value = selectedDeviceId;
            }
            cameraSelect.disabled = cams.length === 0;
        }
    }
    
    async function startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus('Camera API not supported', 'bg-danger');
            return;
        }
        try {
            const constraints = selectedDeviceId 
                ? { video: { deviceId: { exact: selectedDeviceId } }, audio: false }
                : { video: { facingMode: 'user' }, audio: false };
            stream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = stream;
            await video.play();
            fitCanvasToVideo();
            setStatus('Camera ready', 'bg-success');
            if (captureBtn) captureBtn.disabled = false;
            stopBtn.disabled = false;
            startBtn.disabled = true;
            messageEl && (messageEl.textContent = 'Camera initialized.');
            await listCameras();
            await getGeo();
        } catch (err) {
            console.error('Camera error:', err);
            setStatus('Camera permission denied', 'bg-danger');
        }
    }
    
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
        startBtn.disabled = false;
        stopBtn.disabled = true;
        if (captureBtn) captureBtn.disabled = true;
        setStatus('Camera stopped', 'bg-secondary');
    }
    
    function fitCanvasToVideo() {
        if (!video || !canvas) return;
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
    }
    
    function captureFrame() {
        if (!stream) return null;
        fitCanvasToVideo();
        const ctx = canvas.getContext('2d');
        ctx.save();
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        ctx.restore();
        return new Promise(resolve => {
            canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.9);
        });
    }
    
    function setStatus(text, badgeClass) {
        if (!statusEl) return;
        statusEl.textContent = text;
        statusEl.className = `badge ${badgeClass}`;
    }
    
    async function registerFace() {
        const blob = await captureFrame();
        if (!blob) return;
        setStatus('Uploading...', 'bg-info');
        if (captureBtn) {
            captureBtn.disabled = true;
            captureBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        try {
            const form = new FormData();
            form.append('face_image', blob, 'frame.jpg');
            const resp = await fetch('/capture_face', { 
                method: 'POST', 
                body: form,
                cache: 'no-store' // Prevent service worker caching issues
            });
            
            // Check if response was redirected
            if (resp.redirected || resp.status === 302 || resp.status === 301) {
                const redirectUrl = resp.url || resp.headers.get('Location');
                if (redirectUrl) {
                    window.location.href = redirectUrl;
                    return;
                }
            }
            window.location.reload();
        } catch (e) {
            console.error('Register error:', e);
            setStatus('Upload failed', 'bg-danger');
            if (captureBtn) {
                captureBtn.disabled = false;
                captureBtn.innerHTML = '<i class="fas fa-camera me-2"></i>Capture & Register';
            }
        }
    }
    
    async function markAttendance(classId) {
        const blob = await captureFrame();
        if (!blob) return;
        setStatus('Recognizing...', 'bg-info');
        startBtn.disabled = true;
        stopBtn.disabled = false;
        
        try {
            const form = new FormData();
            form.append('face_image', blob, 'frame.jpg');
            if (geo.lat && geo.lng) {
                form.append('latitude', String(geo.lat));
                form.append('longitude', String(geo.lng));
            }
            const resp = await fetch(`/mark_attendance/${classId}`, { 
                method: 'POST', 
                body: form,
                cache: 'no-store' // Prevent service worker caching issues
            });
            
            if (!resp.ok) {
                throw new Error(`HTTP error! status: ${resp.status}`);
            }
            
            // Parse JSON response
            const data = await resp.json();
            if (data.success) {
                setStatus('Attendance marked', 'bg-success');
                messageEl && (messageEl.textContent = data.message);
                if (attendanceList) {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center';
                    li.innerHTML = `
                        <span><i class="fas fa-check-circle text-success me-2"></i>${data.student_name || 'You'}</span>
                        <span class="badge bg-success">${data.time}</span>
                    `;
                    attendanceList.prepend(li);
                }
            } else {
                setStatus('Not recognized', 'bg-warning');
                const msg = data.message || 'Face not recognized. Please try again.';
                messageEl && (messageEl.textContent = msg);
                if (data.needs_registration) {
                    const link = document.createElement('a');
                    link.href = '/capture_face?next=' + encodeURIComponent(window.location.pathname);
                    link.className = 'ms-2';
                    link.textContent = 'Register your face';
                    messageEl && messageEl.appendChild(link);
                }
                startBtn.disabled = false;
                stopBtn.disabled = false;
            }
        } catch (e) {
            console.error('Attendance error:', e);
            setStatus('Error occurred', 'bg-danger');
            messageEl && (messageEl.textContent = 'An error occurred while marking attendance.');
            startBtn.disabled = false;
            stopBtn.disabled = false;
        }
    }
    
    startBtn && startBtn.addEventListener('click', async () => {
        await listCameras();
        await startCamera();
        if (typeof CLASS_ID !== 'undefined' && CLASS_ID) {
            await markAttendance(CLASS_ID);
        }
    });
    stopBtn && stopBtn.addEventListener('click', () => {
        stopCamera();
    });
    captureBtn && captureBtn.addEventListener('click', async () => {
        await registerFace();
    });
    cameraSelect && cameraSelect.addEventListener('change', async () => {
        selectedDeviceId = cameraSelect.value || null;
        if (selectedDeviceId) localStorage.setItem('preferredCameraId', selectedDeviceId);
        if (stream) {
            stopCamera();
            await startCamera();
        }
    });
});
