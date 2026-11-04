(() => {
    const storageKey = 'psu-workspace-navigation-scroll';
    const navigationSelector = '.app-navigation, .admin-navigation';
    const mobileQuery = window.matchMedia('(max-width: 650px)');

    function restoreScrollPosition() {
        if (!mobileQuery.matches) return;

        let savedPosition;
        try {
            savedPosition = Number(sessionStorage.getItem(storageKey));
        } catch (error) {
            console.warn('Workspace navigation position could not be restored.', error);
            return;
        }

        if (!Number.isFinite(savedPosition) || savedPosition <= 0) return;

        requestAnimationFrame(() => {
            document.querySelectorAll(navigationSelector).forEach((navigation) => {
                navigation.scrollLeft = savedPosition;
            });
        });
    }

    document.addEventListener('click', (event) => {
        const link = event.target.closest(`${navigationSelector} a[href]`);
        if (!link || !mobileQuery.matches) return;

        const navigation = link.closest(navigationSelector);
        if (!navigation || navigation.scrollWidth <= navigation.clientWidth) return;

        try {
            sessionStorage.setItem(storageKey, String(navigation.scrollLeft));
        } catch (error) {
            console.warn('Workspace navigation position could not be saved.', error);
        }
    });

    window.addEventListener('pageshow', restoreScrollPosition);
})();
