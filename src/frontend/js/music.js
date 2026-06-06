(function initGlobalMusic() {
    const MUSIC_SRC = 'music/song.mp3';
    const STORAGE_KEY = 'bgMusicEnabled';
    const SESSION_TIME_KEY = 'bgMusicTime';

    let musicButtonEl = null;
    let playErrorHandler = null;
    let startInProgress = null;

    function getAudio() {
        let audio = document.getElementById('bgMusic');
        if (!audio) {
            audio = document.createElement('audio');
            audio.id = 'bgMusic';
            audio.loop = true;
            audio.preload = 'auto';
            audio.src = MUSIC_SRC;
            (document.body || document.documentElement).appendChild(audio);
        }
        return audio;
    }

    function savePlaybackState() {
        const audio = document.getElementById('bgMusic');
        if (!audio) return;
        try {
            sessionStorage.setItem(SESSION_TIME_KEY, String(audio.currentTime || 0));
        } catch (e) {
            /* ignore */
        }
    }

    if (!window.__bgMusicBoot) {
        window.__bgMusicBoot = true;
        getAudio();
        window.addEventListener('pagehide', savePlaybackState);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                savePlaybackState();
            }
        });
    }

    function isMusicEnabled() {
        return localStorage.getItem(STORAGE_KEY) !== 'false';
    }

    function setMusicEnabled(enabled) {
        localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false');
    }

    function updateMusicButton() {
        if (!musicButtonEl) return;
        const audio = getAudio();
        const playing = isMusicEnabled() && !audio.paused;
        musicButtonEl.textContent = playing ? '🎵' : '🔇';
    }

    function waitForCanPlay(audio) {
        if (audio.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
            return Promise.resolve();
        }
        return new Promise((resolve) => {
            audio.addEventListener('canplay', resolve, { once: true });
            audio.addEventListener('error', resolve, { once: true });
        });
    }

    function seekToSavedTime(audio) {
        return new Promise((resolve) => {
            const saved = parseFloat(sessionStorage.getItem(SESSION_TIME_KEY) || '0');
            if (!Number.isFinite(saved) || saved <= 0.5) {
                resolve();
                return;
            }
            if (audio.duration && saved >= audio.duration) {
                resolve();
                return;
            }
            if (Math.abs(audio.currentTime - saved) < 0.25) {
                resolve();
                return;
            }

            const onSeeked = () => {
                audio.removeEventListener('seeked', onSeeked);
                resolve();
            };

            audio.addEventListener('seeked', onSeeked);
            try {
                audio.currentTime = saved;
            } catch (e) {
                audio.removeEventListener('seeked', onSeeked);
                resolve();
            }
        });
    }

    function startPlayback() {
        if (!isMusicEnabled()) {
            return Promise.resolve(false);
        }

        const audio = getAudio();
        if (!audio.paused) {
            return Promise.resolve(true);
        }

        if (startInProgress) {
            return startInProgress;
        }

        startInProgress = waitForCanPlay(audio)
            .then(() => seekToSavedTime(audio))
            .then(() => audio.play())
            .then(() => true)
            .catch(() => false)
            .finally(() => {
                startInProgress = null;
            });

        return startInProgress;
    }

    function resumeIfNeeded() {
        if (!isMusicEnabled()) {
            updateMusicButton();
            return;
        }
        if (!getAudio().paused) {
            return;
        }
        startPlayback().then((ok) => {
            if (!ok && playErrorHandler) {
                playErrorHandler();
            }
            updateMusicButton();
        });
    }

    function bindPlaybackResume() {
        const tryStart = () => resumeIfNeeded();
        document.addEventListener('click', tryStart);
        document.addEventListener('keydown', tryStart);
        window.addEventListener('pageshow', tryStart);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                tryStart();
            }
        });
    }

    function initBackgroundMusic(options = {}) {
        musicButtonEl = options.buttonId
            ? document.getElementById(options.buttonId)
            : null;
        playErrorHandler = typeof options.onPlayError === 'function'
            ? options.onPlayError
            : null;

        resumeIfNeeded();
        bindPlaybackResume();

        setInterval(() => {
            const audio = document.getElementById('bgMusic');
            if (audio && !audio.paused) {
                savePlaybackState();
            }
        }, 1500);

        if (musicButtonEl) {
            musicButtonEl.addEventListener('click', (event) => {
                event.stopPropagation();
                const audio = getAudio();
                if (isMusicEnabled() && !audio.paused) {
                    setMusicEnabled(false);
                    audio.pause();
                    savePlaybackState();
                    updateMusicButton();
                    return;
                }
                setMusicEnabled(true);
                startPlayback()
                    .then((ok) => {
                        if (!ok && playErrorHandler) {
                            playErrorHandler();
                        }
                        updateMusicButton();
                    });
            });
        }
    }

    window.initBackgroundMusic = initBackgroundMusic;
    window.isBackgroundMusicEnabled = isMusicEnabled;

    function boot() {
        const buttonId = document.body.getAttribute('data-music-button');
        initBackgroundMusic({
            buttonId: buttonId || null,
            onPlayError: typeof window.showNotification === 'function'
                ? () => window.showNotification('Не удалось воспроизвести музыку', true)
                : null
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();

(function initUIScale() {
    const VIEWPORT_FILL = 0.75;
    const MIN_SCALE = 0.28;

    const TUTORIAL_DESIGN_W = 550;
    const TUTORIAL_DESIGN_H = 620;
    const TUTORIAL_SIZE_BOOST = 1.05;
    const TUTORIAL_MAX_SCALE = 1.15;
    const TUTORIAL_VIEWPORT_FILL = 0.82;
    const PLANT_DESC_DESIGN_W = 500;
    const PLANT_DESC_DESIGN_H = 580;
    const ACHIEVEMENTS_DESIGN_W = 820;
    const ACHIEVEMENTS_DESIGN_H = 640;
    const REGISTER_DESIGN_W = 600;
    const REGISTER_DESIGN_H = 500;
    const CHOICE_PICKER_DESIGN_W = 580;
    const CHOICE_PICKER_DESIGN_H = 460;

    function viewportScale(designW, designH, fill = VIEWPORT_FILL, maxScale = 1) {
        const raw = Math.min(
            (window.innerWidth * fill) / designW,
            (window.innerHeight * fill) / designH
        );
        return Math.max(MIN_SCALE, Math.min(raw, maxScale));
    }

    function computeTutorialScale() {
        const fitScale = viewportScale(
            TUTORIAL_DESIGN_W,
            TUTORIAL_DESIGN_H,
            TUTORIAL_VIEWPORT_FILL,
            999
        );
        return Math.max(MIN_SCALE, Math.min(fitScale * TUTORIAL_SIZE_BOOST, TUTORIAL_MAX_SCALE));
    }

    function updateUIScale() {
        const root = document.documentElement;
        root.style.setProperty('--tutorial-scale', String(computeTutorialScale()));
        root.style.setProperty('--plant-desc-scale', String(
            viewportScale(PLANT_DESC_DESIGN_W, PLANT_DESC_DESIGN_H)
        ));
        root.style.setProperty('--achievements-scale', String(
            viewportScale(ACHIEVEMENTS_DESIGN_W, ACHIEVEMENTS_DESIGN_H, VIEWPORT_FILL, 1.22)
        ));
        root.style.setProperty('--register-scale', String(
            viewportScale(REGISTER_DESIGN_W, REGISTER_DESIGN_H, 0.82)
        ));
        root.style.setProperty('--choice-picker-scale', String(
            viewportScale(CHOICE_PICKER_DESIGN_W, CHOICE_PICKER_DESIGN_H)
        ));
    }

    updateUIScale();
    window.addEventListener('resize', updateUIScale);
    window.updateUIScale = updateUIScale;
})();
