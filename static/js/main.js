// Main JavaScript for Le Postier

// Disable right-click context menu
document.addEventListener('contextmenu', event => event.preventDefault());

// Enhanced Water particles effect
function createWaterParticles() {
    const particlesContainer = document.createElement('div');
    particlesContainer.className = 'water-particles';
    document.body.appendChild(particlesContainer);

    // Create more visible particles with different sizes
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        setTimeout(() => createParticle(particlesContainer, i), i * 200);
    }
}

function createParticle(container, index) {
    const particle = document.createElement('div');
    
    // Random particle type
    const types = ['particle-small', 'particle-medium', 'particle-large'];
    const type = types[Math.floor(Math.random() * types.length)];
    particle.className = `particle ${type}`;
    
    // Start from different positions across the screen (hidden on left)
    const startY = Math.random() * window.innerHeight;
    particle.style.top = startY + 'px';
    particle.style.left = '-100px'; // Start off-screen
    
    // Random animation duration for variety
    const duration = Math.random() * 10 + 10; // 10-20s
    particle.style.animationDuration = duration + 's';
    
    // Random delay for staggered effect
    particle.style.animationDelay = Math.random() * 2 + 's';
    
    container.appendChild(particle);
    
    // Recreate particle when animation ends
    particle.addEventListener('animationend', () => {
        particle.remove();
        setTimeout(() => createParticle(container, index), Math.random() * 2000);
    });
}

// Initialize water particles on pages with browse or contact
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname;
    if (currentPage.includes('parcourir') || currentPage.includes('browse') || 
        currentPage.includes('contact')) {
        createWaterParticles();
    }
    
    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.alert');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
});

// Navigation functions
function loginSubPopup() {
    const wrapper = document.getElementById('conn_wrapper');
    const triangle = document.getElementById('triangle');
    
    if (!wrapper) return;
    
    if (wrapper.style.opacity == '1') {
        wrapper.style.height = '0';
        wrapper.style.opacity = '0';
        triangle.style.opacity = '0';
    } else {
        wrapper.style.opacity = '1';
        wrapper.style.height = '120px';
        triangle.style.opacity = '1';
    }
}

function burgerMenuToggle() {
    const menuWrapper = document.getElementById('menu_wrapper');
    const triangle = document.getElementById('triangle_1');
    
    if (!menuWrapper) return;
    
    if (menuWrapper.style.opacity == '1') {
        menuWrapper.style.height = '0';
        menuWrapper.style.opacity = '0';
        menuWrapper.style.display = 'none';
        triangle.style.opacity = '0';
    } else {
        menuWrapper.style.display = 'block';
        menuWrapper.style.opacity = '1';
        menuWrapper.style.height = '280px';
        triangle.style.opacity = '1';
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    const connWrapper = document.getElementById('conn_wrapper');
    const menuWrapper = document.getElementById('menu_wrapper');
    const subscribeLink = document.getElementById('subscribe_link');
    const burgerMenu = document.getElementById('burger_menu');
    
    // Handle connection dropdown
    if (connWrapper && !connWrapper.contains(e.target) && 
        e.target !== subscribeLink && 
        !e.target.classList.contains('subscribe')) {
        if (connWrapper.style.opacity == '1') {
            connWrapper.style.height = '0';
            connWrapper.style.opacity = '0';
            const triangle = document.getElementById('triangle');
            if (triangle) triangle.style.opacity = '0';
        }
    }
    
    // Handle burger menu dropdown
    if (menuWrapper && !menuWrapper.contains(e.target) && 
        e.target !== burgerMenu) {
        if (menuWrapper.style.opacity == '1') {
            menuWrapper.style.height = '0';
            menuWrapper.style.opacity = '0';
            menuWrapper.style.display = 'none';
            const triangle = document.getElementById('triangle_1');
            if (triangle) triangle.style.opacity = '0';
        }
    }
});