// Browse Page Specific JavaScript

let currentImageIndex = 0;
let slideInterval;
let postcardImages = [];

// Initialize browse page
document.addEventListener('DOMContentLoaded', () => {
    initializeSearch();
    initializePostcardGrid();
    initializeGlowingWords();
});

// Search functionality
function initializeSearch() {
    const searchForm = document.getElementById('researchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            // Form will submit normally to Django view
            const input = document.getElementById('keywords_input');
            if (input.value.trim() === '') {
                e.preventDefault();
                input.focus();
            }
        });
    }
}

// Theme search
function searchTheme(themeName) {
    document.getElementById('keywords_input').value = themeName;
    document.getElementById('researchForm').submit();
}

// Enhanced glowing words with water effect
function initializeGlowingWords() {
    const words = document.querySelectorAll('.glowing-word');
    
    words.forEach((word, index) => {
        // Add random animation delays for more organic movement
        const flowDelay = Math.random() * 20;
        const waveDelay = Math.random() * 4;
        const glowDelay = Math.random() * 3;
        
        word.style.animationDelay = `${flowDelay}s, ${waveDelay}s, ${glowDelay}s`;
    });
}

// Postcard detail popup
async function showDetail(postcardId) {
    try {
        const response = await fetch(`/api/postcard/${postcardId}/`);
        const data = await response.json();
        
        // Show popup
        document.getElementById('fade').style.display = 'block';
        const popup = document.getElementById('popup_detail');
        popup.style.display = 'block';
        
        // Set image
        const img = document.getElementById('img_popup_detail');
        img.src = data.front_image;
        img.dataset.frontImage = data.front_image;
        img.dataset.backImage = data.back_image;
        
        // Set details
        document.getElementById('p_cp_popup_detail').textContent = data.title;
        document.getElementById('p_nb_cp_popup_detail').textContent = data.number;
        
        // Show/hide arrows based on position
        updateNavigationArrows();
        
    } catch (error) {
        console.error('Error loading postcard details:', error);
    }
}

// Toggle between front and back
function togglePostcardSide() {
    const img = document.getElementById('img_popup_detail');
    const currentSrc = img.src;
    
    if (currentSrc.includes('front') || !currentSrc.includes('back')) {
        img.src = img.dataset.backImage;
    } else {
        img.src = img.dataset.frontImage;
    }
}

// Zoom functionality
async function showZoom(postcardId) {
    try {
        const response = await fetch(`/api/postcard/${postcardId}/zoom/`);
        const data = await response.json();
        
        if (!data.can_view) {
            // Show member card for very rare postcards
            showMemberCard();
            return;
        }
        
        // Show zoom popup
        document.getElementById('fade').style.display = 'block';
        const popup = document.getElementById('popup_zoom');
        popup.style.display = 'block';
        
        const img = document.getElementById('img_popup_zoom');
        img.src = data.front_image;
        
        // Add zoom functionality
        addZoomEffect();
        
    } catch (error) {
        console.error('Error loading zoom view:', error);
    }
}

// Member card popup
function showMemberCard() {
    document.getElementById('fade').style.display = 'block';
    const popup = document.getElementById('popup_non_membre');
    popup.style.display = 'block';
}

// Zoom effect on mouse move
function addZoomEffect() {
    const container = document.getElementById('popup_zoom');
    const img = document.getElementById('img_popup_zoom');
    
    let isZoomed = false;
    
    container.addEventListener('mousemove', (e) => {
        if (!isZoomed) return;
        
        const rect = container.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        
        img.style.transformOrigin = `${x}% ${y}%`;
    });
    
    container.addEventListener('click', () => {
        isZoomed = !isZoomed;
        img.style.transform = isZoomed ? 'scale(2)' : 'scale(1)';
        img.style.cursor = isZoomed ? 'zoom-out' : 'zoom-in';
    });
}

// Navigation for detail popup
function previousImage() {
    if (currentImageIndex > 0) {
        currentImageIndex--;
        updateDetailImage();
    }
}

function nextImage() {
    if (currentImageIndex < postcardImages.length - 1) {
        currentImageIndex++;
        updateDetailImage();
    }
}

function updateDetailImage() {
    const postcard = postcardImages[currentImageIndex];
    document.getElementById('img_popup_detail').src = postcard.front_image;
    document.getElementById('p_cp_popup_detail').textContent = postcard.title;
    document.getElementById('p_nb_cp_popup_detail').textContent = postcard.number;
    updateNavigationArrows();
}

function updateNavigationArrows() {
    const leftArrow = document.getElementById('lat_arrow_0');
    const rightArrow = document.getElementById('lat_arrow_1');
    
    if (leftArrow) {
        leftArrow.style.display = currentImageIndex > 0 ? 'block' : 'none';
    }
    
    if (rightArrow) {
        rightArrow.style.display = currentImageIndex < postcardImages.length - 1 ? 'block' : 'none';
    }
}

// Cinema mode (slideshow)
function cinemaMode() {
    const fade = document.getElementById('fade');
    const slider = document.getElementById('slider');
    
    fade.style.display = 'block';
    slider.style.display = 'block';
    slider.style.opacity = '1';
    
    // Start slideshow
    let currentSlide = 0;
    const slides = slider.querySelectorAll('.slide');
    
    function showSlide(n) {
        slides.forEach(slide => slide.classList.remove('active'));
        slides[n].classList.add('active');
    }
    
    function nextSlide() {
        currentSlide = (currentSlide + 1) % slides.length;
        showSlide(currentSlide);
    }
    
    showSlide(0);
    slideInterval = setInterval(nextSlide, 3000);
}

// Close all popups
function closeAllPopups() {
    document.getElementById('fade').style.display = 'none';
    document.getElementById('popup_detail').style.display = 'none';
    document.getElementById('popup_zoom').style.display = 'none';
    document.getElementById('popup_non_membre').style.display = 'none';
    
    // Stop slideshow if running
    if (slideInterval) {
        clearInterval(slideInterval);
        document.getElementById('slider').style.opacity = '0';
        document.getElementById('slider').style.display = 'none';
    }
}

// Add event listeners for popup controls
document.addEventListener('DOMContentLoaded', () => {
    // Reverse card button
    const reverseBtn = document.getElementById('reverse_cp');
    if (reverseBtn) {
        reverseBtn.addEventListener('click', togglePostcardSide);
    }
    
    // Close buttons
    document.querySelectorAll('.popup_close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            closeAllPopups();
        });
    });
    
    // Fade overlay click
    const fade = document.getElementById('fade');
    if (fade) {
        fade.addEventListener('click', closeAllPopups);
    }
    
    // Initialize postcard grid hover effects
    initializePostcardGrid();
});

// Postcard grid hover effects
function initializePostcardGrid() {
    const postcards = document.querySelectorAll('.cp_result');
    
    postcards.forEach((card, index) => {
        card.addEventListener('mouseenter', () => {
            const details = card.querySelector('.cp_details');
            if (details) {
                details.style.opacity = '1';
            }
        });
        
        card.addEventListener('mouseleave', () => {
            const details = card.querySelector('.cp_details');
            if (details) {
                details.style.opacity = '0';
            }
        });
    });
}

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (document.getElementById('popup_detail').style.display === 'block') {
        if (e.key === 'ArrowLeft') {
            previousImage();
        } else if (e.key === 'ArrowRight') {
            nextImage();
        } else if (e.key === 'Escape') {
            closeAllPopups();
        }
    }
});