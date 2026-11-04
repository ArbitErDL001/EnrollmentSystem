document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-password-toggle]');
    if (!button) return;

    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;

    const showPassword = input.type === 'password';
    input.type = showPassword ? 'text' : 'password';
    button.textContent = showPassword ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(showPassword));
    button.setAttribute(
        'aria-label',
        `${showPassword ? 'Hide' : 'Show'} ${input.labels[0]?.textContent.toLowerCase() || 'password'}`
    );
});
