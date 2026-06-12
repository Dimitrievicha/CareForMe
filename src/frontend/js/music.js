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
