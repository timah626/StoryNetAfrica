// Dashboard functionality
// Dashboard functionality
const TOTAL_STORAGE = 5 * 1024 * 1024 * 1024;
let currentUsedStorage = 0;
let allFiles = [];
let activeCategory = 'all';
let searchQuery = '';

// File type definitions
const fileTypes = {
    documents: ['pdf', 'doc', 'docx', 'txt', 'xlsx'],
    images: ['jpg', 'jpeg', 'png', 'gif'],
    videos: ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm']
};

function getFileCategory(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    for (let category in fileTypes) {
        if (fileTypes[category].includes(ext)) {
            return category;
        }
    }
    return 'other';
}

function getCurrentUsedStorage() {
    return currentUsedStorage;
}

function setCurrentUsedStorage(bytes) {
    currentUsedStorage = bytes;
}

function showCustomAlert(message) {
    document.getElementById('alertMessage').textContent = message;
    document.getElementById('customAlert').style.display = 'flex';
}

function closeAlert() {
    document.getElementById('customAlert').style.display = 'none';
}

// File upload handler
document.getElementById('fileInput').addEventListener('change', handleFileUpload);

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const freeSpace = TOTAL_STORAGE - getCurrentUsedStorage();
    const fileMB = file.size / (1024 * 1024);
    const freeMB = freeSpace / (1024 * 1024);

    if (file.size > freeSpace) {
        showCustomAlert(`Not enough storage!\n\nFile size: ${fileMB.toFixed(2)} MB\nFree space: ${freeMB.toFixed(2)} MB\n\nPlease delete some files first.`);
        document.getElementById('fileInput').value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const uploadPercent = document.getElementById('uploadPercent');
    const uploadFileName = document.getElementById('uploadFileName');

    uploadFileName.textContent = `Uploading: ${file.name}`;
    progressDiv.style.display = 'block';
    progressBar.style.width = '0%';
    uploadPercent.textContent = '0%';

    try {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percent + '%';
                uploadPercent.textContent = percent + '%';
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                progressBar.style.width = '100%';
                uploadPercent.textContent = '100%';
                setTimeout(() => {
                    progressDiv.style.display = 'none';
                    loadFiles();
                    document.getElementById('fileInput').value = '';
                }, 1000);
            } else {
                showCustomAlert('Upload failed');
                progressDiv.style.display = 'none';
            }
        });

        xhr.addEventListener('error', () => {
            showCustomAlert('Upload error');
            progressDiv.style.display = 'none';
        });

        xhr.open('POST', '/upload');
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        progressDiv.style.display = 'none';
    }
}

// Load files from backend
async function loadFiles() {
    try {
        const response = await fetch('/get-files');
        const data = await response.json();

        if (data.success && data.files) {
            allFiles = data.files;
            updateStorageInfo(data.files);
            filterAndDisplayFiles();
        } else {
            allFiles = [];
            displayEmptyState();
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

// Filter files based on category and search
function filterAndDisplayFiles() {
    let filtered = allFiles;

    // Filter by category
    if (activeCategory !== 'all') {
        filtered = filtered.filter(file => getFileCategory(file.name) === activeCategory);
    }

    // Filter by search query
    if (searchQuery.trim() !== '') {
        filtered = filtered.filter(file => 
            file.name.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }

    displayFiles(filtered);
}

function displayEmptyState() {
    const filesList = document.getElementById('filesList');
    filesList.innerHTML = '<div class="empty-state"><p>No files yet. Start by uploading a file!</p></div>';
}

function displayFiles(files) {
    const filesList = document.getElementById('filesList');
    
    if (files.length === 0) {
        filesList.innerHTML = '<div class="empty-state"><p>No files found</p></div>';
        return;
    }

    filesList.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="file-icon">${getFileIcon(file.name)}</div>
            <div class="file-info">
                <p class="file-name">${file.name}</p>
                <p class="file-size">${formatFileSize(file.size)}</p>
            </div>
            

            <div class="file-actions">
                <button class="btn-download" onclick="downloadFile('${file.name}')"><img src="/static/images/download.png" alt="download"></button>
                <button class="btn-delete" onclick="deleteFile('${file.name}')"><img src="/static/images/trash.png" alt="delete"></button>
            </div>
        </div>
    `).join('');
}

function updateStorageInfo(files) {
    let totalUsed = 0;
    let docs = 0, images = 0, videos = 0, other = 0;

    files.forEach(file => {
        totalUsed += file.size;
        const category = getFileCategory(file.name);

        if (category === 'documents') docs += file.size;
        else if (category === 'images') images += file.size;
        else if (category === 'videos') videos += file.size;
        else other += file.size;
    });

    setCurrentUsedStorage(totalUsed);

    const totalFree = TOTAL_STORAGE - totalUsed;
    const usedPercent = (totalUsed / TOTAL_STORAGE) * 100;

    const usedGB_raw = totalUsed / (1024 * 1024 * 1024);
    const freeGB_raw = totalFree / (1024 * 1024 * 1024);

    let displayUsedValue, displayUsedUnit;
    let displayFreeValue, displayFreeUnit;

    if (usedGB_raw < 0.01) {
        displayUsedValue = (totalUsed / (1024 * 1024)).toFixed(2);
        displayUsedUnit = "MB";
        displayFreeValue = (totalFree / (1024 * 1024)).toFixed(2);
        displayFreeUnit = "MB";
    } else {
        displayUsedValue = usedGB_raw.toFixed(2);
        displayUsedUnit = "GB";
        displayFreeValue = freeGB_raw.toFixed(2);
        displayFreeUnit = "GB";
    }

    document.getElementById("usedGB").textContent = displayUsedValue;
    document.getElementById("usedText").textContent = `${displayUsedValue} ${displayUsedUnit} Used`;
    document.getElementById("freeText").textContent = `${displayFreeValue} ${displayFreeUnit} Free`;
    document.getElementById("usedUnit").textContent = displayUsedUnit;

    const circle = document.querySelector('.storage-used');
    if (circle) {
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (usedPercent / 100) * circumference;
        circle.style.strokeDasharray = circumference;
        circle.style.strokeDashoffset = offset;
    }

    // Format storage display function
    function formatStorageSize(bytes) {
        const mb = bytes / (1024 * 1024);
        if (mb >= 1024) {
            return (mb / 1024).toFixed(2) + ' GB';
        }
        return mb.toFixed(1) + ' MB';
    }

    document.getElementById('docsSize').textContent = formatStorageSize(docs);
    document.getElementById('imagesSize').textContent = formatStorageSize(images);
    document.getElementById('videosSize').textContent = formatStorageSize(videos);
    document.getElementById('otherSize').textContent = formatStorageSize(other);

    const docsPercent = totalUsed > 0 ? (docs / totalUsed) * 100 : 0;
    const imagesPercent = totalUsed > 0 ? (images / totalUsed) * 100 : 0;
    const videosPercent = totalUsed > 0 ? (videos / totalUsed) * 100 : 0;
    const otherPercent = totalUsed > 0 ? (other / totalUsed) * 100 : 0;

    document.querySelector('.breakdown-fill.docs').style.width = docsPercent + '%';
    document.querySelector('.breakdown-fill.images').style.width = imagesPercent + '%';
    document.querySelector('.breakdown-fill.videos').style.width = videosPercent + '%';
    document.querySelector('.breakdown-fill.other').style.width = otherPercent + '%';
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    
    if (fileTypes.documents.includes(ext)) return '<img src="/static/images/documents.png" alt="Document" class="file-icon-img">';
    if (fileTypes.images.includes(ext)) return '<img src="/static/images/images.png" alt="Image" class="file-icon-img">';
    if (fileTypes.videos.includes(ext)) return '<img src="/static/images/movies.png" alt="Video" class="file-icon-img">';
    return '<img src="/static/images/files.png" alt="File" class="file-icon-img">';
}



function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

async function downloadFile(filename) {
    window.location.href = `/download/${filename}`;
}

function showDeleteConfirm(filename) {
    const overlay = document.createElement('div');
    overlay.className = 'custom-alert-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML = `
        <div class="custom-alert-box">
            <p>Are you sure you want to delete <strong>${filename}</strong>?</p>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button onclick="this.closest('.custom-alert-overlay').remove()" class="alert-btn" style="background: #6c757d;">Cancel</button>
                <button onclick="confirmDelete('${filename}'); this.closest('.custom-alert-overlay').remove();" class="alert-btn" style="background: #dc3545;">Delete</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

async function confirmDelete(filename) {
    try {
        const response = await fetch(`/delete/${filename}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            loadFiles();
        } else {
            showCustomAlert(data.error || 'Delete failed');
        }
    } catch (error) {
        showCustomAlert('Error deleting file');
    }
}

async function deleteFile(filename) {
    showDeleteConfirm(filename);
}

// Category switching
document.querySelectorAll('.category-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.category-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        activeCategory = item.dataset.category;
        filterAndDisplayFiles();
    });
});

// Search functionality
document.getElementById('searchInput').addEventListener('input', (e) => {
    searchQuery = e.target.value;
    filterAndDisplayFiles();
});

// Load files on page load
window.addEventListener('load', loadFiles);

