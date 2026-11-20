(function () {
    const sesion = JSON.parse(sessionStorage.getItem('usuario_sesion') || 'null');
    if (!sesion) {
        window.location.replace('/login');
        return;
    }

    // Inyecta X-Usuario en cada llamada a la API
    const _fetchOriginal = window.fetch;
    window.fetch = async function (input, options = {}) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';

        if (url.includes('/api/') || url.startsWith('api/')) {
            const headers = new Headers(options.headers || (input instanceof Request ? input.headers : undefined));
            headers.set('X-Usuario', sesion.usuario);
            options = { ...options, headers };
        }

        return _fetchOriginal(input, options);
    };
})();