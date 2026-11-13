/* Configuración pública del prototipo. Este archivo nunca debe contener secretos.
 * Si Render cambia de dirección, cambia apiUrl y sincroniza la copia del frontend.
 * En localhost y Render, app.js utiliza el mismo origen de la página.
 * En GitHub Pages utiliza apiUrl, porque Pages solo publica archivos estáticos.
 */
window.LA_SALLE_CONFIG = Object.freeze({
  apiUrl: "https://formulario-la-salle.onrender.com",
  modo: "prototipo",
  tiempoEsperaMs: 65000
});
