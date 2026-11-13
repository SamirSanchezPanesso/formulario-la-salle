/* Capturas OPCIONALES con Chromium real, para ejecutar en un equipo compatible.
 * Este script no constituye evidencia hasta que el usuario lo ejecuta.
 * Usa la aplicación local, modo prototipo y datos ficticios; no llama a Render.
 * Preparación: npm ci; npx playwright install chromium; npm run capturas.
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const {spawn} = require("node:child_process");
const {chromium} = require("playwright");

const RAIZ = path.resolve(__dirname, "..");
const SALIDA = path.resolve(process.argv[2] || path.join(__dirname, "capturas_navegador"));
const PYTHON = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

async function iniciarServidor(temporal) {
  // port=0 hace que el sistema operativo elija un puerto libre, sin carreras.
  const codigo = [
    "import json",
    "import app",
    "servidor=app.create_server('127.0.0.1', 0)",
    "print(json.dumps({'puerto': servidor.server_address[1]}), flush=True)",
    "servidor.serve_forever()",
  ].join("\n");
  const proceso = spawn(PYTHON, ["-u", "-c", codigo], {
    cwd: path.join(RAIZ, "Form/formulario"),
    env: {...process.env, APP_ENV: "testing", HOST: "127.0.0.1", PORT: "0", ALLOWED_ORIGINS: "", DATABASE_PATH: path.join(temporal, "capturas.db")},
    stdio: ["ignore", "pipe", "pipe"],
  });
  let errores = "";
  proceso.stderr.on("data", bloque => { errores += bloque.toString(); });
  const puerto = await new Promise((resolver, rechazar) => {
    let texto = "";
    const limite = setTimeout(() => { proceso.kill(); rechazar(new Error("El servidor local no arrancó: " + errores)); }, 15000);
    proceso.on("error", error => { clearTimeout(limite); rechazar(error); });
    proceso.on("exit", codigoSalida => { clearTimeout(limite); rechazar(new Error(`Servidor detenido (${codigoSalida}): ${errores}`)); });
    proceso.stdout.on("data", bloque => {
      texto += bloque.toString();
      const primeraLinea = texto.split("\n")[0];
      if (!texto.includes("\n")) return;
      try { const dato = JSON.parse(primeraLinea); clearTimeout(limite); resolver(dato.puerto); }
      catch (error) { clearTimeout(limite); rechazar(error); }
    });
  });
  return {proceso, base: `http://127.0.0.1:${puerto}`};
}

(async () => {
  const temporal = fs.mkdtempSync(path.join(os.tmpdir(), "lasalle_capturas_"));
  let servidor;
  let navegador;
  const archivos = [];
  try {
    fs.mkdirSync(SALIDA, {recursive: true});
    servidor = await iniciarServidor(temporal);
    navegador = await chromium.launch({headless: true});
    const contexto = await navegador.newContext({viewport: {width: 1440, height: 1100}, locale: "es-ES", deviceScaleFactor: 1});
    const pagina = await contexto.newPage();
    const capturar = async (nombre, paginaActual = pagina) => {
      await paginaActual.screenshot({path: path.join(SALIDA, nombre), fullPage: true, animations: "disabled"});
      archivos.push(nombre);
    };
    await pagina.goto(servidor.base + "/?modo=prototipo#/inicio", {waitUntil: "networkidle"});
    await capturar("01_inicio.png");
    await pagina.locator('[data-nav="contacto"]').click();
    await pagina.locator("#screen-contacto").waitFor({state: "visible"});
    await capturar("02_formulario.png");
    await pagina.locator("#example-button").click();
    await pagina.locator("#email").fill("correo-invalido");
    await pagina.locator("#submit-button").click();
    await pagina.locator("#error-summary").waitFor({state: "visible"});
    await capturar("03_error.png");
    await pagina.locator("#email").fill("elena.garcia@example.com");
    await pagina.locator("#submit-button").click();
    await pagina.locator("#screen-confirmacion").waitFor({state: "visible"});
    await capturar("04_confirmacion.png");

    const contextoMovil = await navegador.newContext({viewport: {width: 390, height: 844}, locale: "es-ES", deviceScaleFactor: 1, isMobile: true, hasTouch: true});
    const movil = await contextoMovil.newPage();
    await movil.goto(servidor.base + "/?modo=prototipo#/inicio", {waitUntil: "networkidle"});
    await capturar("05_inicio_movil.png", movil);
    await movil.locator('[data-nav="contacto"]').click();
    await movil.locator("#screen-contacto").waitFor({state: "visible"});
    await capturar("06_formulario_movil.png", movil);
    fs.writeFileSync(path.join(SALIDA, "capturas_resultado.json"), JSON.stringify({
      fecha_utc: new Date().toISOString(), ejecutado: true, navegador: "Chromium",
      version_navegador: navegador.version(), node: process.version,
      modo: "prototipo local; datos ficticios; sin llamadas a Render",
      archivos,
    }, null, 2) + "\n");
    console.log(`Capturas obtenidas en ${SALIDA}`);
    console.log("Son capturas de esta ejecución local. Revisar visualmente antes de entregarlas.");
  } finally {
    if (navegador) await navegador.close();
    if (servidor && servidor.proceso.exitCode === null) {
      await new Promise(resolver => {
        const limite = setTimeout(resolver, 2000);
        servidor.proceso.once("exit", () => { clearTimeout(limite); resolver(); });
        servidor.proceso.kill();
      });
    }
    fs.rmSync(temporal, {recursive: true, force: true});
  }
})().catch(error => {
  console.error(error.stack);
  console.error("Revisa Python y ejecuta: npx playwright install chromium. Si tu equipo limita Chromium, realiza las capturas manualmente en tu navegador.");
  process.exitCode = 1;
});
