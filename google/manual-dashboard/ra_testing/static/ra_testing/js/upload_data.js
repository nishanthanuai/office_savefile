
document.addEventListener('DOMContentLoaded', function () {

    // --- ELEMENT SELECTORS --------
    const manageImagesForm = document.getElementById('manageImagesForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const fetchImagesBtn = document.getElementById('fetchImagesBtn');
    const deleteImagesBtn = document.getElementById('deleteImagesBtn');
    const processImagesBtn = document.getElementById('processImagesBtn');
    const imageGrid = document.getElementById('imageGrid');
    const surveyIdInput = document.getElementById('surveyId');
    const roadIdInput = document.getElementById('roadId');
    const modelTypeSelect = document.getElementById('model_type');
    const imageUploadInput = document.getElementById('imageUpload');
    const imageUploadMultipleInput = document.getElementById('imageUploadMultiple');

    // --- UTILITY FUNCTIONS ---

    /**
     * Gets the CSRF token from cookies.
     */
    function getCsrfToken() {
        return document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    /**
     * GENERATES A RANDOM NAME (This was missing in your code!)
     */
    function generateUniqueName() {
        // Creates a name like: img_1703456123_a9b3c
        const timestamp = new Date().getTime();
        const randomStr = Math.random().toString(36).substring(2, 8);
        return `img_${timestamp}_${randomStr}`;
    }

    /**
     * Displays a Bootstrap alert.
     */
    function showAlert(message, type = 'success') {
        const alertPlaceholder = document.getElementById('alertPlaceholder');
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
        alertPlaceholder.append(wrapper);

        setTimeout(() => {
            wrapper.querySelector('.alert')?.classList.remove('show');
            wrapper.addEventListener('transitionend', () => wrapper.remove());
        }, 5000);
    }
    
    function toggleButtonLoading(button, isLoading) {
        if (!button) return;
        const spinner = button.querySelector('.spinner-border');
        button.disabled = isLoading;
        if (spinner) {
            spinner.style.display = isLoading ? 'inline-block' : 'none';
        }
    }

    function saveFormState() {
        localStorage.setItem('surveyId', surveyIdInput.value);
        localStorage.setItem('roadId', roadIdInput.value);
        localStorage.setItem('modelType', modelTypeSelect.value);
    }

    function loadFormState() {
        surveyIdInput.value = localStorage.getItem('surveyId') || '';
        roadIdInput.value = localStorage.getItem('roadId') || '';
        modelTypeSelect.value = localStorage.getItem('modelType') || 'furniture';
    }


    // --- EVENT LISTENERS ---

    loadFormState();
    surveyIdInput.addEventListener('change', saveFormState);
    roadIdInput.addEventListener('change', saveFormState);
    modelTypeSelect.addEventListener('change', saveFormState);


    // 1. UPLOAD IMAGES (With Renaming Fix)
    manageImagesForm.addEventListener('submit', function (e) {
        e.preventDefault();
        saveFormState(); 
        
        const formData = new FormData(manageImagesForm);
        
        // Collect files from both inputs using the new field names
        const folderFiles = imageUploadInput.files;
        const multipleFiles = imageUploadMultipleInput.files;
        
        // Combine both file lists
        const allFiles = [...folderFiles, ...multipleFiles];

        if (allFiles.length === 0) {
            showAlert('Please select one or more images to upload.', 'warning');
            return;
        }

        // Remove existing images entries from FormData
        formData.delete('images_folder');
        formData.delete('images_multiple');

        // 2. Loop, Rename, and Re-append
        allFiles.forEach(file => {
            const extension = file.name.split('.').pop();
            const newName = generateUniqueName() + '.' + extension; 
            
            // Create renamed file
            const renamedFile = new File([file], newName, { type: file.type });
            formData.append('images', renamedFile);
            
            console.log(`Renaming: ${file.name} -> ${newName}`);
        });
        // ----------------------

        const xhr = new XMLHttpRequest();
        const progressBarContainer = document.getElementById('progressBarContainer');
        const progressBar = document.getElementById('progressBar');

        xhr.open('POST', manageImagesForm.action, true);
        xhr.setRequestHeader('X-CSRFToken', getCsrfToken());

        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        progressBarContainer.style.display = 'block';
        toggleButtonLoading(uploadBtn, true);

        xhr.upload.addEventListener('progress', function (event) {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                progressBar.style.width = `${percentComplete}%`;
                progressBar.setAttribute('aria-valuenow', percentComplete);
                progressBar.textContent = `${percentComplete}%`;
            }
        });

        xhr.onload = function () {
            toggleButtonLoading(uploadBtn, false);
            setTimeout(() => { progressBarContainer.style.display = 'none'; }, 2000);

            if (xhr.status >= 200 && xhr.status < 300) {
                showAlert('Images uploaded successfully!', 'success');
                // Clear both inputs
                imageUploadInput.value = ''; 
                imageUploadMultipleInput.value = '';
                fetchImages(); 
            } else {
                showAlert(`Upload failed: ${xhr.statusText}`, 'danger');
            }
        };

        xhr.onerror = function () {
            toggleButtonLoading(uploadBtn, false);
            progressBarContainer.style.display = 'none';
            showAlert('Network error occurred.', 'danger');
        };

        xhr.send(formData);
    });

    // 2. FETCH IMAGES
    fetchImagesBtn.addEventListener('click', () => {
        saveFormState();
        fetchImages();
    });

    // 3. DELETE ALL IMAGES
    deleteImagesBtn.addEventListener('click', async function () {
        saveFormState();
        if (!confirm('Delete ALL images for this survey/road? This cannot be undone.')) {
            return;
        }

        const surveyId = surveyIdInput.value;
        const roadId = roadIdInput.value;
        const modelType = modelTypeSelect.value;

        toggleButtonLoading(deleteImagesBtn, true);
        try {
            const response = await fetch('/delete_all/', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ surveyId, roadId, model_type: modelType }),
            });
            const data = await response.json();
            if (response.ok && data.success) {
                showAlert('All images deleted.', 'success');
                renderImages([]); 
            } else {
                showAlert(`Failed: ${data.error || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert(`Error: ${error.message}`, 'danger');
        } finally {
            toggleButtonLoading(deleteImagesBtn, false);
        }
    });

    // 4. PROCESS IMAGES
    processImagesBtn.addEventListener('click', function() {
        saveFormState();
        const surveyId = surveyIdInput.value;
        const roadId = roadIdInput.value;
        const modelType = modelTypeSelect.value;

        if (!surveyId || !roadId) {
            showAlert("Please enter Survey ID and Road ID.", "warning");
            return;
        }
        
        const processUrl = `/process/?surveyId=${surveyId}&roadId=${roadId}&model_type=${modelType}`;
        showAlert("Redirecting to process images...", "info");
        setTimeout(() => { window.location.href = processUrl; }, 1500);
    });

    // 5. DELETE SINGLE IMAGE
    imageGrid.addEventListener('click', function(event) {
        const deleteButton = event.target.closest('.delete-image-btn');
        if (deleteButton) {
            deleteSingleImage(deleteButton);
        }
    });

    // --- CORE LOGIC ---
    
    async function fetchImages() {
        const surveyId = surveyIdInput.value;
        const roadId = roadIdInput.value;
        const modelType = modelTypeSelect.value;
        const url = `/fetch-images/?surveyId=${surveyId}&roadId=${roadId}&model_type=${modelType}`;

        toggleButtonLoading(fetchImagesBtn, true);
        imageGrid.innerHTML = `
            <div class="col-12 text-center p-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2 text-muted">Loading...</p>
            </div>`;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(response.statusText);
            const data = await response.json();
            renderImages(data.images);
        } catch (error) {
            showAlert(`Error: ${error.message}`, 'danger');
            imageGrid.innerHTML = '<div class="col-12 text-center text-danger p-5"><p>Could not load images.</p></div>';
        } finally {
            toggleButtonLoading(fetchImagesBtn, false);
        }
    }

    function renderImages(images) {
        imageGrid.innerHTML = '';
        if (images && images.length > 0) {
            images.forEach((image,index) => {
                const col = document.createElement('div');
                col.className = 'col-md-6 col-lg-4 mb-4 image-card-container';
                col.innerHTML = `
                    <div class="card h-100 shadow-sm">
                        <img src="${image.url}" class="card-img-top" alt="${image.name}" loading="lazy">
                        <div class="card-body d-flex flex-column">
                            <p class="card-text small text-muted text-truncate" title="${image.name}">Frame ${index + 1}</p>
                            <button class="btn btn-outline-danger btn-sm delete-image-btn mt-auto" data-image-name="${image.name}">
                                Delete
                            </button>
                        </div>
                    </div>`;
                imageGrid.appendChild(col);
            });
        } else {
            imageGrid.innerHTML = '<div class="col-12 text-center text-muted p-5"><p>No images found.</p></div>';
        }
    }

    async function deleteSingleImage(button) {
        const imageName = button.dataset.imageName;
        if (!confirm(`Delete image: ${imageName}?`)) return;

        const surveyId = surveyIdInput.value;
        const roadId = roadIdInput.value;
        const modelType = modelTypeSelect.value;
        
        toggleButtonLoading(button, true);
        try {
            const response = await fetch('/delete_image/', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ image_name: imageName, surveyId, roadId, model_type: modelType }),
            });
            const data = await response.json();

            if (response.ok && data.success) {
                showAlert('Image deleted.', 'success');
                const cardContainer = button.closest('.image-card-container');
                if (cardContainer) {
                    cardContainer.style.opacity = '0';
                    setTimeout(() => cardContainer.remove(), 500);
                }
            } else {
                showAlert(`Failed: ${data.error}`, 'danger');
                toggleButtonLoading(button, false);
            }
        } catch (error) {
            showAlert(`Error: ${error.message}`, 'danger');
            toggleButtonLoading(button, false);
        }
    }
});