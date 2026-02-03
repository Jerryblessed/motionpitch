let current = 0; 
const total = document.querySelectorAll('.slide').length;

function show(idx) { 
    document.querySelectorAll('.slide').forEach(el => el.classList.remove('active')); 
    const slide = document.getElementById('slide-' + idx);
    if (slide) {
        slide.classList.add('active');
        
        // Autoplay videos when slide becomes active
        const video = slide.querySelector('video');
        if (video) {
            video.play().catch(e => console.log('Video autoplay prevented:', e));
        }
    }
}

function next() { 
    if(current < total - 1) { 
        current++; 
        show(current); 
    } 
}

function prev() { 
    if(current > 0) { 
        current--; 
        show(current); 
    } 
}

document.addEventListener('keydown', (e) => { 
    if(e.key === 'ArrowRight') next(); 
    if(e.key === 'ArrowLeft') prev(); 
});

// Initialize first slide
show(current);
