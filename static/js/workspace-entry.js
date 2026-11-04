(() => {
    const storageKey = 'psu-workspace-entry-played';
    const isWorkspace = document.querySelector('.app-layout, .admin-dashboard');

    if (!isWorkspace) {
        try {
            sessionStorage.removeItem(storageKey);
        } catch (error) {
            console.warn('Workspace animation preference could not be reset.', error);
        }
        return;
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    try {
        if (sessionStorage.getItem(storageKey) === 'true') return;
        sessionStorage.setItem(storageKey, 'true');
    } catch (error) {
        console.warn('Workspace animation preference could not be saved.', error);
    }

    document.body.classList.add('workspace-enter');
})();
