const NOT_FOUND_DESIGN_W = 1280;
const NOT_FOUND_DESIGN_H = 720;

function updateNotFoundScale() {
    const scale = Math.min(
        window.innerWidth / NOT_FOUND_DESIGN_W,
        window.innerHeight / NOT_FOUND_DESIGN_H
    );
    document.documentElement.style.setProperty('--not-found-scale', String(scale));
}

updateNotFoundScale();
window.addEventListener('resize', updateNotFoundScale);
