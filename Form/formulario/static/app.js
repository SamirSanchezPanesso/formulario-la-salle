/* Formulario La Salle: navegación accesible y validación sin dependencias.
 * Los nombres de los campos JSON se conservan para ser compatibles con la API.
 * El modo prototipo no hace peticiones de red ni persiste datos personales.
 */
"use strict";

(() => {
  const configuracion = window.LA_SALLE_CONFIG || {};
  const parametros = new URLSearchParams(window.location.search);
  const modoSolicitado = parametros.get("modo") || configuracion.modo;
  const esPrototipo = modoSolicitado !== "conectado";
  const formulario = document.getElementById("contact-form");
  const campos = ["name", "email", "subject", "message"];
  const nombres = {name: "Nombre completo", email: "Correo electrónico", subject: "Asunto", message: "Mensaje"};
  const limites = {name: [2, 100], email: [3, 254], subject: [3, 120], message: [10, 2000]};
  // Las mismas reglas de formato que validators.py. El formato no demuestra
  // que una cuenta exista; en esta actividad no se envían correos de verificación.
  const patronCorreo = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$/;
  const botonEnviar = document.getElementById("submit-button");
  const etiquetaEnviar = document.getElementById("submit-label");
  const botonEjemplo = document.getElementById("example-button");
  const resumen = document.getElementById("error-summary");
  const listaErrores = document.getElementById("error-list");
  const avisoConexion = document.getElementById("connection-message");
  const estadoAccesible = document.getElementById("status");
  let erroresActuales = {};
  let hayIntento = false;
  let enviando = false;
  let numeroDemostracion = 0;
  let recibo = null;
  let temporizadorLento = null;

  // Pages publica archivos estáticos. Render y el servidor local alojan también
  // la API, por lo que allí usamos el mismo origen sin pedir al usuario editar URL.
  function obtenerBaseApi() {
    const esPages = window.location.hostname.endsWith(".github.io");
    if (!esPages && /^https?:$/.test(window.location.protocol)) return window.location.origin;
    const url = String(configuracion.apiUrl || "").replace(/\/+$/, "");
    if (!/^https?:\/\//.test(url)) throw new Error("CONFIGURACION_API");
    return url;
  }

  function actualizarTextosModo() {
    if (esPrototipo) return;
    document.getElementById("mode-pill").lastChild.textContent = "Aplicación académica";
    document.getElementById("home-mode-note").textContent = "Prueba académica con registro de datos. Usa información ficticia.";
    document.getElementById("form-mode-note").textContent = "Prueba académica: los datos se guardan en esta aplicación. Usa información ficticia; no es un canal oficial de La Salle.";
    document.getElementById("help-mode-text").textContent = "Si el servidor registra tu mensaje, verás una referencia. Esta aplicación no envía correos ni gestiona atención institucional.";
    document.getElementById("send-note").textContent = "Se registrará el mensaje en la aplicación académica. No se envían correos.";
    document.getElementById("footer-note").textContent = "Aplicación académica · Registro de prueba";
    etiquetaEnviar.textContent = "Registrar consulta";
    botonEjemplo.hidden = true;
  }

  function datosFormulario() {
    return Object.fromEntries(campos.map((campo) => [campo, document.getElementById(campo).value.trim()]));
  }

  function validarCampo(campo, valor) {
    if (!valor) return "Completa este campo.";
    const [minimo, maximo] = limites[campo];
    const longitud = Array.from(valor).length;
    if (longitud < minimo) return `Escribe al menos ${minimo} caracteres.`;
    if (longitud > maximo) return `Usa como máximo ${maximo} caracteres.`;
    if (campo === "email") {
      const parteLocal = valor.slice(0, valor.lastIndexOf("@"));
      if (!patronCorreo.test(valor) || parteLocal.length > 64 || parteLocal.startsWith(".") || parteLocal.endsWith(".") || parteLocal.includes("..")) {
        return "Escribe un correo válido, por ejemplo nombre@ejemplo.com.";
      }
    }
    return "";
  }

  function validar(datos) {
    const errores = {};
    campos.forEach((campo) => {
      const mensaje = validarCampo(campo, datos[campo]);
      if (mensaje) errores[campo] = mensaje;
    });
    return errores;
  }

  // Nunca insertamos texto del usuario con innerHTML. Los errores devueltos por
  // el servidor se muestran como texto y solo se asocian a campos conocidos.
  function mostrarErrores(errores, moverFoco = false) {
    erroresActuales = Object.fromEntries(Object.entries(errores).filter(([campo]) => campos.includes(campo)));
    listaErrores.replaceChildren();
    campos.forEach((campo) => {
      const entrada = document.getElementById(campo);
      const mensaje = document.getElementById(`${campo}-error`);
      const error = erroresActuales[campo];
      mensaje.hidden = !error;
      mensaje.textContent = error || "";
      if (error) {
        entrada.setAttribute("aria-invalid", "true");
        const elemento = document.createElement("li");
        const enlace = document.createElement("a");
        enlace.href = `#${campo}`;
        enlace.textContent = `${nombres[campo]}: ${error}`;
        enlace.addEventListener("click", (evento) => {
          evento.preventDefault();
          entrada.focus();
          entrada.scrollIntoView({block: "center", behavior: "auto"});
        });
        elemento.append(enlace);
        listaErrores.append(elemento);
      } else {
        entrada.removeAttribute("aria-invalid");
      }
    });
    resumen.hidden = Object.keys(erroresActuales).length === 0;
    if (!resumen.hidden && moverFoco) requestAnimationFrame(() => resumen.focus());
  }

  function actualizarContador() {
    const cantidad = Array.from(document.getElementById("message").value).length;
    const contador = document.getElementById("message-counter");
    contador.textContent = `${cantidad} / 2000`;
    contador.classList.toggle("over-limit", cantidad > 2000);
  }

  function rutaActual() {
    const ruta = window.location.hash.replace(/^#\/?/, "");
    return ["inicio", "contacto", "error", "confirmacion"].includes(ruta) ? ruta : "inicio";
  }

  function navegar(ruta) {
    if (window.location.hash === `#/${ruta}`) renderizarRuta(true);
    else window.location.hash = `/${ruta}`;
  }

  // Las rutas de error y confirmación representan estados auténticos de la sesión.
  // Abrir una URL de confirmación sin haber enviado no inventa un registro.
  function renderizarRuta(moverFoco = true) {
    let ruta = rutaActual();
    if ((ruta === "confirmacion" && !recibo) || (ruta === "error" && !Object.keys(erroresActuales).length && avisoConexion.hidden)) {
      ruta = "contacto";
      history.replaceState(null, "", "#/contacto");
    }
    const pantalla = ruta === "error" ? "contacto" : ruta;
    document.querySelectorAll("[data-screen]").forEach((seccion) => {
      seccion.hidden = seccion.dataset.screen !== pantalla;
    });
    document.querySelectorAll("[data-nav]").forEach((enlace) => {
      const activo = enlace.dataset.nav === (pantalla === "inicio" ? "inicio" : "contacto");
      if (activo) enlace.setAttribute("aria-current", "page");
      else enlace.removeAttribute("aria-current");
    });
    const titulos = {inicio: "Inicio", contacto: "Formulario", error: "Revisar consulta", confirmacion: "Confirmación"};
    document.title = `${titulos[ruta]} · Contacto La Salle`;
    if (moverFoco) {
      const destino = ruta === "error" ? (!resumen.hidden ? resumen : avisoConexion) : document.getElementById(`title-${pantalla}`);
      requestAnimationFrame(() => {
        destino.focus({preventScroll: true});
        if (ruta === "error") destino.scrollIntoView({block: "start", behavior: "auto"});
        else window.scrollTo({top: 0, behavior: "auto"});
      });
    }
  }

  function cambiarOcupado(valor) {
    enviando = valor;
    botonEnviar.disabled = valor;
    botonEjemplo.disabled = valor;
    formulario.setAttribute("aria-busy", String(valor));
    campos.forEach((campo) => { document.getElementById(campo).readOnly = valor; });
    etiquetaEnviar.textContent = valor ? (esPrototipo ? "Comprobando…" : "Registrando…") : (esPrototipo ? "Enviar consulta de prueba" : "Registrar consulta");
    if (!valor) clearTimeout(temporizadorLento);
  }

  function mostrarConfirmacion(datos, resultado) {
    recibo = {datos, resultado};
    const referencia = esPrototipo ? `DEMO-${String(++numeroDemostracion).padStart(3, "0")}` : `LS-${String(resultado.id).padStart(6, "0")}`;
    document.getElementById("receipt-reference").textContent = referencia;
    document.getElementById("receipt-email").textContent = datos.email;
    document.getElementById("receipt-subject").textContent = datos.subject;
    document.getElementById("confirmation-description").textContent = esPrototipo
      ? `Gracias, ${datos.name}. La consulta de ejemplo ha pasado la validación. Así se muestra el cierre del recorrido.`
      : `Gracias, ${datos.name}. El servidor ha confirmado el registro de tu mensaje. Puedes identificarlo con esta referencia.`;
    if (!esPrototipo) {
      const titulo = document.getElementById("title-confirmacion");
      titulo.textContent = "Mensaje registrado.";
      document.getElementById("reference-label").textContent = "Referencia del registro";
      document.getElementById("confirmation-note").textContent = "El mensaje se ha guardado en esta aplicación académica. No se ha enviado ningún correo ni una solicitud a los servicios de La Salle.";
    }
    navegar("confirmacion");
  }

  async function enviarAlServidor(datos) {
    const controlador = new AbortController();
    const espera = Number(configuracion.tiempoEsperaMs) || 65000;
    const tiempoLimite = setTimeout(() => controlador.abort(), espera);
    try {
      const respuesta = await fetch(`${obtenerBaseApi()}/api/contact`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "omit",
        body: JSON.stringify(datos),
        signal: controlador.signal
      });
      let resultado;
      try { resultado = await respuesta.json(); }
      catch (_) { throw new Error("RESPUESTA_INVALIDA"); }
      if (!respuesta.ok || !resultado.ok) {
        if (respuesta.status === 422 && resultado.errors && typeof resultado.errors === "object") {
          mostrarErrores(resultado.errors);
          if (!resumen.hidden) { navegar("error"); return null; }
        }
        if (respuesta.status === 403) throw new Error("ORIGEN_NO_PERMITIDO");
        throw new Error("SERVIDOR_NO_CONFIRMADO");
      }
      if (!Number.isInteger(resultado.id) || resultado.id < 1) throw new Error("RESPUESTA_INVALIDA");
      return resultado;
    } finally { clearTimeout(tiempoLimite); }
  }

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (enviando) return; // Evita dos registros por un doble clic rápido.
    hayIntento = true;
    avisoConexion.hidden = true;
    const datos = datosFormulario();
    const errores = validar(datos);
    mostrarErrores(errores);
    if (Object.keys(errores).length) {
      estadoAccesible.textContent = "Hay datos por corregir. Revisa el resumen de errores.";
      navegar("error");
      return;
    }
    cambiarOcupado(true);
    estadoAccesible.textContent = esPrototipo ? "Comprobando la consulta de ejemplo." : "Esperando la confirmación del registro.";
    if (!esPrototipo) {
      temporizadorLento = setTimeout(() => {
        estadoAccesible.className = "form-bottom-note";
        estadoAccesible.textContent = "El servicio está tardando en responder. Conservamos tus datos; espera la confirmación antes de volver a enviar.";
      }, 7000);
    }
    try {
      // La pausa permite percibir el estado de envío, sin tocar la API ni SQLite.
      const resultado = esPrototipo
        ? await new Promise((resolver) => setTimeout(() => resolver({ok: true, modo: "prototipo"}), 550))
        : await enviarAlServidor(datos);
      if (resultado) {
        mostrarConfirmacion(datos, resultado);
        formulario.reset();
        hayIntento = false;
        actualizarContador();
        estadoAccesible.textContent = esPrototipo ? "Envío de prueba completado." : "Mensaje registrado.";
      }
    } catch (error) {
      let mensaje = "No pudimos confirmar el registro. Tus datos siguen aquí. Comprueba la conexión antes de intentarlo de nuevo; la aplicación no puede descartar que el servidor haya recibido el intento anterior.";
      if (error.name === "AbortError") mensaje = "El servicio tardó demasiado y no pudimos confirmar el resultado. Conservamos tus datos. Evita reenviar varias veces seguidas: el intento anterior podría haberse registrado.";
      if (error.message === "ORIGEN_NO_PERMITIDO") mensaje = "El servidor no permite registrar consultas desde esta dirección. Tus datos se conservan. Consulta la configuración del proyecto antes de reintentar.";
      if (error.message === "CONFIGURACION_API") mensaje = "No se encuentra configurada la dirección del servicio. Tus datos siguen en el formulario.";
      avisoConexion.textContent = mensaje;
      avisoConexion.hidden = false;
      estadoAccesible.textContent = "No se ha podido confirmar el registro.";
      navegar("error");
    } finally {
      cambiarOcupado(false);
      estadoAccesible.className = "sr-only";
    }
  });

  campos.forEach((campo) => {
    const entrada = document.getElementById(campo);
    entrada.addEventListener("input", () => {
      if (campo === "message") actualizarContador();
      // No mostramos errores mientras la persona escribe por primera vez.
      // Después del primer intento, retiramos cada error en cuanto se corrige.
      if (hayIntento && erroresActuales[campo]) {
        const mensaje = validarCampo(campo, entrada.value.trim());
        // No reconstruir role=alert con el mismo texto evita anuncios repetidos
        // del lector de pantalla en cada pulsación.
        if (mensaje === erroresActuales[campo]) return;
        const nuevos = {...erroresActuales};
        if (mensaje) nuevos[campo] = mensaje; else delete nuevos[campo];
        mostrarErrores(nuevos);
      }
    });
  });

  botonEjemplo.addEventListener("click", () => {
    const ejemplo = {name: "Elena García", email: "elena.garcia@example.com", subject: "Información sobre actividades", message: "Hola. Me gustaría conocer qué actividades académicas están disponibles y cómo puedo participar. Muchas gracias."};
    campos.forEach((campo) => { document.getElementById(campo).value = ejemplo[campo]; });
    mostrarErrores({});
    avisoConexion.hidden = true;
    actualizarContador();
    estadoAccesible.textContent = "Datos ficticios cargados. Puedes editarlos antes de enviar la prueba.";
    document.getElementById("name").focus();
  });

  document.getElementById("another-button").addEventListener("click", () => {
    formulario.reset();
    recibo = null;
    hayIntento = false;
    mostrarErrores({});
    avisoConexion.hidden = true;
    actualizarContador();
    navegar("contacto");
  });

  // Un enlace de salto evita cambiar de pantalla. El hash de ruta se conserva.
  document.querySelector(".skip-link").addEventListener("click", (evento) => {
    evento.preventDefault();
    document.getElementById("contenido").focus();
  });
  window.addEventListener("hashchange", () => renderizarRuta(true));
  actualizarTextosModo();
  actualizarContador();
  renderizarRuta(false);
})();
