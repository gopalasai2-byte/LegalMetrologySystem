// Legal Metrology Compliance System - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const dropzoneContent = document.getElementById('dropzoneContent');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const uploadForm = document.getElementById('uploadForm');
    const processingIndicator = document.getElementById('processingIndicator');
    const submitBtn = document.getElementById('submitBtn');

    if (dropzone && fileInput) {
        // Drag & Drop events
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                fileInput.files = files;
                handleFileSelect(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (fileInput.files && fileInput.files[0]) {
                handleFileSelect(fileInput.files[0]);
            }
        });

        if (removeFileBtn) {
            removeFileBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.value = '';
                previewContainer.classList.add('d-none');
                dropzoneContent.classList.remove('d-none');
            });
        }
    }

    function handleFileSelect(file) {
        if (!file.type.match('image.*')) {
            alert('Please select a valid image file (JPG, PNG, WEBP).');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            fileNameDisplay.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
            dropzoneContent.classList.add('d-none');
            previewContainer.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
    }

    // Submit form handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', () => {
            if (fileInput && fileInput.files.length > 0) {
                if (processingIndicator) {
                    processingIndicator.classList.remove('d-none');
                }
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Analyzing Label with OpenCV & OCR...';
                }
            }
        });
    }

    // --- Real-Time Auto-Update for Statistics Cards ---
    function fetchAndUpdateStats() {
        const statsRow = document.getElementById('statsOverviewRow');
        if (!statsRow) return;

        fetch('/api/stats')
            .then(response => {
                if (!response.ok) throw new Error('Network error');
                return response.json();
            })
            .then(data => {
                if (data && data.success && data.stats) {
                    const s = data.stats;
                    updateStatValue('stat-total', s.total);
                    updateStatValue('stat-passed', s.passed);
                    updateStatValue('stat-failed', s.failed);
                    updateStatValue('stat-review', s.review);
                    updateStatValue('stat-avg', (s.avg_score !== undefined ? s.avg_score : 0) + '%');
                }
            })
            .catch(() => {
                // Silently ignore transient network interruptions
            });
    }

    function updateStatValue(elementId, newValue) {
        const el = document.getElementById(elementId);
        if (!el) return;
        const currentVal = el.textContent.trim();
        const strVal = String(newValue).trim();
        if (currentVal !== strVal) {
            el.textContent = strVal;
            el.classList.remove('stat-updated-pulse');
            void el.offsetWidth; // Force CSS reflow
            el.classList.add('stat-updated-pulse');
        }
    }

    if (document.getElementById('statsOverviewRow')) {
        // Poll every 3 seconds for immediate updates after any label scan
        setInterval(fetchAndUpdateStats, 3000);

        // Immediate fetch when window gains focus or tab becomes active
        window.addEventListener('focus', fetchAndUpdateStats);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                fetchAndUpdateStats();
            }
        });

        // Handle Back-Forward Cache (bfcache) when navigating back
        window.addEventListener('pageshow', () => {
            fetchAndUpdateStats();
        });
    }
});
