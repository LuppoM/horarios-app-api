(function () {
    // 1. Inyectar los estilos CSS del relojito automáticamente
    const style = document.createElement("style");
    style.textContent = `
        #global-loader-overlay {
            position: fixed;
            inset: 0;
            background: rgba(255, 255, 255, 0.72);
            backdrop-filter: blur(2px);
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 99999;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        #global-loader-overlay.activo {
            display: flex;
        }
        .global-spinner {
            width: 48px;
            height: 48px;
            border: 5px solid #d0e1f9;
            border-top: 5px solid #004080;
            border-radius: 50%;
            animation: spin-palmesano 0.8s linear infinite;
            margin-bottom: 12px;
        }
        .global-loader-texto {
            color: #004080;
            font-weight: bold;
            font-size: 11pt;
        }
        @keyframes spin-palmesano {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

    let overlay = null;
    let peticionesActivas = 0;
    let esDescargaArchivo = false;
    let timerSeguridadUnload = null;

    const PALABRAS_DESCARGA = [
        "pdf",
        "exportar",
        "consolidado",
        "descargar",
        "download",
        "excel",
        "csv",
        "reporte",
        "imprimir"
    ];

    function asegurarOverlay() {
        if (overlay) return overlay;
        overlay = document.createElement("div");
        overlay.id = "global-loader-overlay";
        overlay.innerHTML = `
            <div class="global-spinner"></div>
            <div class="global-loader-texto" id="global-loader-msg">Cargando, por favor espere...</div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }

    window.mostrarRelojito = function (mensaje = "Cargando, por favor espere...") {
        const el = asegurarOverlay();
        const txt = document.getElementById("global-loader-msg");
        if (txt) txt.textContent = mensaje;
        el.classList.add("activo");
        document.body.style.cursor = "wait";
    };

    window.ocultarRelojito = function () {
        if (timerSeguridadUnload) {
            clearTimeout(timerSeguridadUnload);
            timerSeguridadUnload = null;
        }
        if (!overlay) return;
        overlay.classList.remove("activo");
        document.body.style.cursor = "default";
    };

    // 2. Detectar clics en cualquier botón/enlace de descarga (PDF, Consolidado, etc.)
    document.addEventListener("click", function (e) {
        const target = e.target.closest("button, a, input[type='button'], input[type='submit']");
        if (!target) return;

        const firma = [
            target.textContent || "",
            target.value || "",
            target.id || "",
            target.getAttribute("onclick") || "",
            target.getAttribute("href") || ""
        ].join(" ").toLowerCase();

        if (PALABRAS_DESCARGA.some(palabra => firma.includes(palabra))) {
            esDescargaArchivo = true;
            setTimeout(() => { esDescargaArchivo = false; }, 4000);
        }
    }, true);

    // 3. Interceptar TODOS los fetch() de la aplicación automáticamente
    const fetchOriginal = window.fetch;
    window.fetch = async function (...args) {
        peticionesActivas++;
        if (peticionesActivas === 1) {
            const url = typeof args[0] === "string" ? args[0].toLowerCase() : "";
            let msg = "Cargando datos...";
            if (url.includes("guardar")) {
                msg = "Guardando cambios...";
            } else if (PALABRAS_DESCARGA.some(p => url.includes(p))) {
                msg = "Generando archivo...";
            }
            window.mostrarRelojito(msg);
        }

        try {
            return await fetchOriginal.apply(this, args);
        } finally {
            peticionesActivas = Math.max(0, peticionesActivas - 1);
            if (peticionesActivas === 0) {
                window.ocultarRelojito();
            }
        }
    };

    // 4. Mostrar relojito al navegar, con corte automático si la página no cambia (descarga directa)
    window.addEventListener("beforeunload", function () {
        if (esDescargaArchivo) return;
        window.mostrarRelojito("Abriendo pantalla...");

        if (timerSeguridadUnload) clearTimeout(timerSeguridadUnload);
        timerSeguridadUnload = setTimeout(() => {
            if (peticionesActivas === 0) {
                window.ocultarRelojito();
            }
        }, 2500);
    });

    // 5. Limpiar el overlay si el usuario vuelve atrás en el navegador (bfcache)
    window.addEventListener("pageshow", function () {
        if (peticionesActivas === 0) {
            window.ocultarRelojito();
        }
    });
})();