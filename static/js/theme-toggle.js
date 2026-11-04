(() => {
    const root = document.documentElement;
    const storageKey = 'psu-enrollment-theme';
    let transitionTimer;

    const applyTheme = (theme) => {
        root.dataset.theme = theme;
        document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
            const lightMode = theme === 'light';
            button.textContent = lightMode ? '☾ Dark' : '☀ Light';
            button.setAttribute('aria-label', `Switch to ${lightMode ? 'dark' : 'light'} mode`);
            button.setAttribute('aria-pressed', String(lightMode));
            button.title = `Switch to ${lightMode ? 'dark' : 'light'} mode`;
        });
    };

    let theme = 'dark';
    try {
        theme = localStorage.getItem(storageKey) === 'light' ? 'light' : 'dark';
    } catch (error) {
        console.error('Unable to read the saved color theme:', error);
    }
    applyTheme(theme);
    document.addEventListener('DOMContentLoaded', () => applyTheme(theme), { once: true });

    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-theme-toggle]');
        if (!button) return;

        window.clearTimeout(transitionTimer);
        root.classList.add('theme-transition');
        theme = root.dataset.theme === 'light' ? 'dark' : 'light';
        applyTheme(theme);
        transitionTimer = window.setTimeout(() => {
            root.classList.remove('theme-transition');
        }, 300);
        try {
            localStorage.setItem(storageKey, theme);
        } catch (error) {
            console.error('Unable to save the selected color theme:', error);
        }
    });
})();
