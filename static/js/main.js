// Unregister any existing service workers to prevent Response.clone() errors
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(registrations) {
        for(let registration of registrations) {
            registration.unregister().then(function(success) {
                if (success) {
                    console.log('Service worker unregistered successfully');
                }
            });
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((a) => {
        setTimeout(() => {
            a.classList.remove('show');
        }, 5000);
    });
    
    const path = window.location.pathname;
    document.querySelectorAll('.navbar .nav-link').forEach(link => {
        try {
            const href = new URL(link.href, window.location.origin).pathname;
            if (href === path) {
                link.classList.add('active');
            }
        } catch (_) {}
    });
    
    const fileInput = document.getElementById('profile_image');
    const previewEl = document.getElementById('profile_image_preview');
    if (fileInput && previewEl) {
        fileInput.addEventListener('change', () => {
            const file = fileInput.files && fileInput.files[0];
            if (file) {
                const url = URL.createObjectURL(file);
                previewEl.src = url;
            }
        });
    }
}); 
