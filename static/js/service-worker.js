const CACHE_NAME = 'psu-enrollment-shell-v35';
const CORE_ASSETS = [
    '/static/site.webmanifest',
    '/static/images/psu-app-icon.svg',
    '/static/css/styles.css',
    '/static/css/admin-dashboard.css',
    '/static/css/login.css',
    '/static/js/password-toggle.js',
    '/static/js/pwa.js',
    '/static/js/confirm-actions.js',
    '/static/js/table-tools.js',
    '/static/js/workspace-navigation.js',
    '/static/js/theme-toggle.js',
    '/static/js/workspace-entry.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(CORE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys
                    .filter((key) => key.startsWith('psu-enrollment-') && key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    if (request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.open(CACHE_NAME).then(async (cache) => {
                const cached = await cache.match(request);
                if (cached) return cached;

                const response = await fetch(request);
                if (response.ok) await cache.put(request, response.clone());
                return response;
            })
        );
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() => new Response(
                '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#111314"><title>Offline | PSU Enrollment</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#111314;color:#f7f0e9;font:16px Arial,sans-serif"><main style="max-width:28rem;padding:2rem;text-align:center"><strong style="color:#ff8a2a">Palawan State University</strong><h1>You are offline</h1><p>Reconnect to the internet to access your enrollment account and current student information.</p><button onclick="location.reload()" style="padding:.7rem 1rem;border:0;border-radius:6px;background:#ff8a2a;color:#111314;font-weight:700">Try again</button></main></body></html>',
                { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
            ))
        );
    }
});
