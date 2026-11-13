/* Pruebas del DOM con JSDOM. No son pruebas de un navegador gráfico.
 * Se cargan el HTML, config.js y app.js reales del proyecto. Solo se simulan
 * fetch, scrollTo, scrollIntoView y requestAnimationFrame. Los escenarios de
 * red son respuestas controladas; la API real se verifica en la suite Python.
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {execFileSync} = require("node:child_process");
const {JSDOM, VirtualConsole} = require("jsdom");

const RAIZ = path.resolve(__dirname, "..");
const HTML = fs.readFileSync(path.join(RAIZ, "docs/index.html"), "utf8");
const CONFIG = fs.readFileSync(path.join(RAIZ, "docs/config.js"), "utf8");
const APP = fs.readFileSync(path.join(RAIZ, "docs/app.js"), "utf8");
const POSICION_SALIDA = process.argv.indexOf("--output");
const SALIDA = POSICION_SALIDA >= 0 ? path.resolve(process.argv[POSICION_SALIDA + 1]) : path.join(__dirname, "resultados");
const VALIDO = {name: "Elena García", email: "elena@example.com", subject: "Información académica", message: "Quisiera conocer las actividades académicas disponibles."};
const escenarios = [];
const resultados = [];
function caso(nombre, ejecutar) { escenarios.push({nombre, ejecutar}); }
function pausa(ms = 10) { return new Promise(resolver => setTimeout(resolver, ms)); }
async function esperar(condicion, mensaje, limite = 1800) {
  const inicio = Date.now();
  while (!condicion()) {
    if (Date.now() - inicio > limite) throw new Error("Espera agotada: " + mensaje);
    await pausa(5);
  }
}
function respuesta(status, contenido) {
  return {ok: status >= 200 && status < 300, status, json: async () => contenido};
}
function crear(opciones = {}) {
  const consola = new VirtualConsole();
  const errores = [];
  consola.on("jsdomError", error => errores.push(error.message));
  const dom = new JSDOM(HTML, {
    url: opciones.url || `https://samirsanchezpanesso.github.io/formulario-la-salle/${opciones.conectado ? "?modo=conectado" : ""}${opciones.hash || "#/inicio"}`,
    runScripts: "outside-only",
    pretendToBeVisual: true,
    virtualConsole: consola,
    // No se activa resources: JSDOM no descarga CSS, imágenes ni scripts.
  });
  const w = dom.window;
  const llamadas = [];
  w.scrollTo = () => {};
  w.HTMLElement.prototype.scrollIntoView = () => {};
  w.requestAnimationFrame = accion => w.setTimeout(() => accion(Date.now()), 0);
  w.fetch = (url, opcionesFetch) => {
    llamadas.push({url, opciones: opcionesFetch});
    if (opciones.fetch) return opciones.fetch(url, opcionesFetch);
    return Promise.reject(new Error("Una prueba sin red intentó llamar fetch."));
  };
  w.eval(CONFIG);
  if (opciones.config) w.LA_SALLE_CONFIG = Object.freeze({...w.LA_SALLE_CONFIG, ...opciones.config});
  w.eval(APP);
  const d = w.document;
  return {
    dom, w, d, llamadas, errores,
    campo(id) { return d.getElementById(id); },
    completar(datos = VALIDO) {
      for (const [id, valor] of Object.entries(datos)) {
        d.getElementById(id).value = valor;
        d.getElementById(id).dispatchEvent(new w.Event("input", {bubbles: true}));
      }
    },
    enviar() { d.getElementById("contact-form").dispatchEvent(new w.Event("submit", {bubbles: true, cancelable: true})); },
    cerrar() { w.close(); },
  };
}
async function usar(opciones, ejecutar) {
  const entorno = crear(opciones);
  try { await ejecutar(entorno); assert.deepEqual(entorno.errores, [], "Sin errores internos de JSDOM"); }
  finally { entorno.cerrar(); }
}
function verificarSinExito(e) {
  assert.equal(e.campo("screen-confirmacion").hidden, true);
  assert.equal(e.campo("screen-contacto").hidden, false);
  assert.equal(e.campo("submit-button").disabled, false);
}
function verificarDatos(e, datos = VALIDO) {
  for (const [campo, valor] of Object.entries(datos)) assert.equal(e.campo(campo).value, valor);
}

caso("Inicio y navegación al formulario con foco y aria-current", async () => {
  await usar({}, async e => {
    assert.equal(e.campo("screen-inicio").hidden, false);
    assert.equal(e.campo("screen-contacto").hidden, true);
    e.d.querySelector('[data-nav="contacto"]').click();
    await esperar(() => !e.campo("screen-contacto").hidden && e.d.activeElement.id === "title-contacto", "formulario y foco");
    assert.equal(e.d.title, "Formulario · Contacto La Salle");
    assert.equal(e.d.querySelector('[data-nav="contacto"]').getAttribute("aria-current"), "page");
    assert.equal(e.d.querySelector('[data-nav="inicio"]').hasAttribute("aria-current"), false);
    e.d.querySelector(".skip-link").click();
    assert.equal(e.d.activeElement.id, "contenido");
    assert.equal(e.w.location.hash, "#/contacto");
  });
});

caso("Campos vacíos: cuatro errores, foco en resumen y enlace al campo", async () => {
  await usar({hash: "#/contacto"}, async e => {
    e.enviar();
    await esperar(() => e.w.location.hash === "#/error" && e.d.activeElement.id === "error-summary", "resumen de errores");
    assert.equal(e.campo("error-list").children.length, 4);
    for (const campo of Object.keys(VALIDO)) assert.equal(e.campo(campo).getAttribute("aria-invalid"), "true");
    e.d.querySelector('#error-list a[href="#email"]').click();
    assert.equal(e.d.activeElement.id, "email");
    assert.equal(e.w.location.hash, "#/error");
    assert.equal(e.llamadas.length, 0);
  });
});

caso("Correo incorrecto conserva datos y elimina su error al corregirlo", async () => {
  await usar({hash: "#/contacto"}, async e => {
    const datos = {...VALIDO, email: "correo-invalido"};
    e.completar(datos); e.enviar();
    await esperar(() => !e.campo("error-summary").hidden, "error de correo");
    verificarDatos(e, datos);
    assert.equal(e.campo("email-error").hidden, false);
    e.completar({email: VALIDO.email});
    assert.equal(e.campo("email-error").hidden, true);
    assert.equal(e.campo("email").hasAttribute("aria-invalid"), false);
    assert.equal(e.campo("error-summary").hidden, true);
    assert.equal(e.llamadas.length, 0);
  });
});

caso("Reglas de correo equivalentes a validators.py en 18 ejemplos", async () => {
  const correo254 = "a".repeat(64) + "@" + "b".repeat(63) + "." + "c".repeat(63) + "." + "d".repeat(61);
  const correos = ["ana@example.com", "nombre+curso@example.co", "o'connor@example.com", "correo-invalido", "ana@", "@example.com", "ana@example", ".ana@example.com", "ana.@example.com", "a..b@example.com", "ana@-example.com", "ana@example-.com", "ana@exa_mple.com", "á@example.com", "a".repeat(65) + "@example.com", correo254, correo254 + "a", "  ana@example.com  "];
  const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const codigo = "import json,sys;sys.path.insert(0,sys.argv[1]);from validators import validate_contact;datos=json.load(sys.stdin);print(json.dumps([('email' not in validate_contact(dict(name='Ana',email=x,subject='Consulta',message='Mensaje de prueba'))) for x in datos]))";
  const esperados = JSON.parse(execFileSync(python, ["-c", codigo, path.join(RAIZ, "Form/formulario")], {input: JSON.stringify(correos), encoding: "utf8"}));
  for (let i = 0; i < correos.length; i++) {
    await usar({hash: "#/contacto"}, async e => {
      e.completar({...VALIDO, email: correos[i]}); e.enviar();
      const aceptado = e.campo("submit-button").disabled;
      assert.equal(aceptado, esperados[i], `Misma decisión que Python: ${correos[i]}`);
      assert.equal(e.llamadas.length, 0);
    });
  }
});

caso("Contador Unicode y límite de 2000 caracteres, sin contar pares UTF-16 doble", async () => {
  await usar({hash: "#/contacto"}, async e => {
    e.completar({...VALIDO, message: "😀".repeat(10)});
    assert.equal(e.campo("message-counter").textContent, "10 / 2000");
    e.completar({message: "😀".repeat(2001)}); e.enviar();
    assert.equal(e.campo("message-counter").textContent, "2001 / 2000");
    assert.equal(e.campo("message-counter").classList.contains("over-limit"), true);
    assert.equal(e.campo("message").getAttribute("aria-invalid"), "true");
    assert.equal(e.campo("submit-button").disabled, false);
    e.completar({message: "😀".repeat(2000)}); e.enviar();
    assert.equal(e.campo("submit-button").disabled, true, "2000 puntos de código son válidos");
    assert.equal(e.campo("message-counter").classList.contains("over-limit"), false);
  });
});

caso("Límites de nombre, asunto y mensaje antes de cualquier envío", async () => {
  for (const [campo, minimo, maximo] of [["name", 2, 100], ["subject", 3, 120], ["message", 10, 2000]]) {
    for (const [cantidad, valido] of [[minimo - 1, false], [minimo, true], [maximo, true], [maximo + 1, false]]) {
      await usar({hash: "#/contacto"}, async e => {
        e.completar({...VALIDO, [campo]: "x".repeat(cantidad)}); e.enviar();
        assert.equal(e.campo("submit-button").disabled, valido, `${campo}: ${cantidad}`);
      });
    }
  }
});

caso("Demostración completa sin fetch ni almacenamiento del navegador", async () => {
  await usar({hash: "#/contacto"}, async e => {
    e.campo("example-button").click();
    assert.equal(e.d.activeElement.id, "name");
    assert.ok(e.campo("email").value.endsWith("@example.com"));
    e.enviar();
    assert.equal(e.campo("contact-form").getAttribute("aria-busy"), "true");
    await esperar(() => !e.campo("screen-confirmacion").hidden && e.d.activeElement.id === "title-confirmacion", "confirmación de demostración");
    assert.equal(e.campo("receipt-reference").textContent, "DEMO-001");
    assert.match(e.campo("confirmation-note").textContent, /simulado/);
    assert.equal(e.llamadas.length, 0);
    assert.equal(e.w.localStorage.length, 0);
    assert.equal(e.w.sessionStorage.length, 0);
    assert.equal(e.campo("contact-form").getAttribute("aria-busy"), "false");
    for (const campo of Object.keys(VALIDO)) assert.equal(e.campo(campo).value, "");
  });
});

caso("No se inventa confirmación ni error al abrir sus rutas directamente", async () => {
  for (const hash of ["#/confirmacion", "#/error"]) {
    await usar({hash}, async e => {
      assert.equal(e.w.location.hash, "#/contacto");
      assert.equal(e.campo("screen-confirmacion").hidden, true);
      assert.equal(e.campo("screen-contacto").hidden, false);
      assert.equal(e.campo("receipt-reference").textContent, "");
    });
  }
});

caso("Otra consulta borra recibo previo y permite comenzar otra vez", async () => {
  await usar({hash: "#/contacto"}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("screen-confirmacion").hidden, "primera confirmación");
    e.campo("another-button").click();
    await esperar(() => e.w.location.hash === "#/contacto" && !e.campo("screen-contacto").hidden, "otra consulta");
    for (const campo of Object.keys(VALIDO)) assert.equal(e.campo(campo).value, "");
    assert.equal(e.campo("message-counter").textContent, "0 / 2000");
    e.w.location.hash = "/confirmacion";
    await esperar(() => e.w.location.hash === "#/contacto", "confirmación bloqueada tras reinicio");
  });
});

caso("Fallo de red simulado: conserva datos y no muestra éxito", async () => {
  await usar({conectado: true, hash: "#/contacto", fetch: async () => { throw new TypeError("Red simulada no disponible"); }}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("connection-message").hidden && e.d.activeElement.id === "connection-message", "aviso de conexión y foco");
    verificarDatos(e); verificarSinExito(e);
    assert.match(e.campo("connection-message").textContent, /no puede descartar/);
    assert.equal(e.llamadas.length, 1);
  });
});

caso("Respuesta 422 simulada: errores del servidor como texto seguro", async () => {
  const mensaje = "<b>Revisa el correo indicado</b>";
  await usar({conectado: true, hash: "#/contacto", fetch: async () => respuesta(422, {ok: false, errors: {email: mensaje, desconocido: "Ignorar"}})}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("error-summary").hidden && !e.campo("submit-button").disabled, "validación de servidor");
    verificarDatos(e); verificarSinExito(e);
    assert.equal(e.campo("email-error").textContent, mensaje);
    assert.equal(e.campo("email-error").querySelector("b"), null);
    assert.equal(e.campo("error-list").children.length, 1);
  });
});

caso("Respuesta 201 simulada: referencia, contrato JSON y limpieza final", async () => {
  await usar({conectado: true, hash: "#/contacto", fetch: async () => respuesta(201, {ok: true, id: 42, message: "Mensaje registrado correctamente."})}, async e => {
    assert.equal(e.campo("example-button").hidden, true);
    e.completar({...VALIDO, name: "  Elena García  "}); e.enviar();
    await esperar(() => !e.campo("screen-confirmacion").hidden, "confirmación conectada simulada");
    assert.equal(e.llamadas.length, 1);
    assert.equal(e.llamadas[0].url, "https://formulario-la-salle.onrender.com/api/contact");
    assert.equal(e.llamadas[0].opciones.method, "POST");
    assert.equal(e.llamadas[0].opciones.credentials, "omit");
    assert.deepEqual(JSON.parse(e.llamadas[0].opciones.body), VALIDO);
    assert.equal(e.campo("receipt-reference").textContent, "LS-000042");
    assert.equal(e.campo("receipt-email").textContent, VALIDO.email);
    assert.equal(e.campo("title-confirmacion").textContent, "Mensaje registrado.");
    assert.match(e.campo("confirmation-note").textContent, /No se ha enviado ningún correo/);
    assert.equal(e.campo("name").value, "");
  });
});

caso("Doble envío bloqueado mientras fetch simulado está pendiente", async () => {
  let resolver;
  await usar({conectado: true, hash: "#/contacto", fetch: () => new Promise(r => { resolver = r; })}, async e => {
    e.completar(); e.enviar(); e.enviar();
    assert.equal(e.llamadas.length, 1);
    assert.equal(e.campo("submit-button").disabled, true);
    assert.equal(e.campo("contact-form").getAttribute("aria-busy"), "true");
    for (const campo of Object.keys(VALIDO)) assert.equal(e.campo(campo).readOnly, true);
    resolver(respuesta(201, {ok: true, id: 7}));
    await esperar(() => !e.campo("screen-confirmacion").hidden, "fin del único envío");
    assert.equal(e.llamadas.length, 1);
    assert.equal(e.campo("submit-button").disabled, false);
    for (const campo of Object.keys(VALIDO)) assert.equal(e.campo(campo).readOnly, false);
  });
});

caso("No confirma respuestas exitosas sin identificador válido", async () => {
  for (const id of [undefined, 0, -1, "42"]) {
    await usar({conectado: true, hash: "#/contacto", fetch: async () => respuesta(201, {ok: true, id})}, async e => {
      e.completar(); e.enviar();
      await esperar(() => !e.campo("connection-message").hidden, "respuesta inválida");
      verificarDatos(e); verificarSinExito(e);
    });
  }
});

caso("Respuesta 403 simulada informa origen no autorizado y conserva datos", async () => {
  await usar({conectado: true, hash: "#/contacto", fetch: async () => respuesta(403, {ok: false})}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("connection-message").hidden, "error de origen");
    assert.match(e.campo("connection-message").textContent, /no permite/);
    verificarDatos(e); verificarSinExito(e);
  });
});

caso("Tiempo agotado simulado informa incertidumbre sin perder datos", async () => {
  await usar({conectado: true, hash: "#/contacto", config: {tiempoEsperaMs: 30}, fetch: (_, opciones) => new Promise((resolver, rechazar) => {
    opciones.signal.addEventListener("abort", () => { const error = new Error("Tiempo de prueba"); error.name = "AbortError"; rechazar(error); });
  })}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("connection-message").hidden, "tiempo de espera");
    assert.match(e.campo("connection-message").textContent, /podría haberse registrado/);
    verificarDatos(e); verificarSinExito(e);
  });
});

caso("En Render y localhost se usa la API del mismo origen", async () => {
  await usar({url: "http://127.0.0.1:8123/?modo=conectado#/contacto", fetch: async () => respuesta(201, {ok: true, id: 3})}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("screen-confirmacion").hidden, "API mismo origen");
    assert.equal(e.llamadas[0].url, "http://127.0.0.1:8123/api/contact");
  });
});

caso("URL API ausente en Pages produce aviso y ninguna llamada de red", async () => {
  await usar({conectado: true, hash: "#/contacto", config: {apiUrl: ""}}, async e => {
    e.completar(); e.enviar();
    await esperar(() => !e.campo("connection-message").hidden, "configuración ausente");
    assert.match(e.campo("connection-message").textContent, /No se encuentra configurada/);
    assert.equal(e.llamadas.length, 0);
    verificarDatos(e); verificarSinExito(e);
  });
});

(async () => {
  const inicio = new Date();
  const lineas = ["JSDOM: pruebas de comportamiento DOM; no navegador gráfico ni red real."];
  for (const {nombre, ejecutar} of escenarios) {
    const marca = Date.now();
    try {
      await ejecutar();
      resultados.push({nombre, resultado: "OK", duracion_ms: Date.now() - marca});
      lineas.push("OK - " + nombre);
    } catch (error) {
      resultados.push({nombre, resultado: "FALLO", duracion_ms: Date.now() - marca, error: error.stack});
      lineas.push("FALLO - " + nombre + "\n" + error.stack);
    }
  }
  const fallos = resultados.filter(item => item.resultado === "FALLO").length;
  const informe = {
    inicio_utc: inicio.toISOString(), fin_utc: new Date().toISOString(),
    node: process.version, jsdom: require("jsdom/package.json").version,
    alcance: "HTML y JavaScript reales ejecutados en JSDOM; fetch simulado en escenarios conectados. No prueba de navegador, disposición visual ni red real.",
    stubs: ["fetch", "scrollTo", "scrollIntoView", "requestAnimationFrame"],
    total: resultados.length, aprobados: resultados.length - fallos, fallos, casos: resultados,
  };
  lineas.push(`Resultado: ${informe.aprobados}/${informe.total} aprobados; ${fallos} fallos.`);
  fs.mkdirSync(SALIDA, {recursive: true});
  fs.writeFileSync(path.join(SALIDA, "dom_resultado.json"), JSON.stringify(informe, null, 2) + "\n");
  fs.writeFileSync(path.join(SALIDA, "dom_pruebas.log"), lineas.join("\n") + "\n");
  console.log(lineas.join("\n"));
  process.exitCode = fallos ? 1 : 0;
})().catch(error => { console.error(error.stack); process.exitCode = 2; });
