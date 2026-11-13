# Pruebas del rediseño La Salle

## Qué se comprueba

El proyecto contiene dos suites que se complementan:

| Suite | Alcance | Red y datos |
|---|---|---|
| `Form/formulario/tests/test_redisenio_backend.py` | 22 casos de validación, HTTP, SQLite, CORS, rutas públicas y recuperación de errores | Servidor HTTP real local y base SQLite temporal |
| `probar_dom.cjs` | 18 escenarios sobre el HTML y JavaScript reales: navegación, foco, errores, conservación de datos, Unicode, confirmación y bloqueo de doble envío | JSDOM; las respuestas de `fetch` son simuladas y se identifican como tales |

JSDOM ejecuta el comportamiento del DOM, pero no es un navegador gráfico. Estas pruebas no certifican la disposición visual, el contraste, el recorrido con tabulador ni el funcionamiento de un lector de pantalla. La revisión visual se documenta por separado. Las únicas sustituciones del entorno DOM son `fetch`, `scrollTo`, `scrollIntoView` y `requestAnimationFrame`.

El modo prototipo se comprueba sin peticiones de red y sin datos guardados en `localStorage` o `sessionStorage`. Los casos conectados simulan respuestas 201, 422 y 403, fallos de red y tiempo agotado. La persistencia real se verifica en Python. No se envían consultas al servicio público de Render.

## Ejecutar el backend

Desde la raíz del repositorio, con Python 3.10 o superior:

```bash
python -m unittest discover -s Form/formulario/tests -p test_redisenio_backend.py -v
```

En algunos sistemas Linux/macOS el comando es `python3`. La suite usa una base temporal y no abre bases que contengan consultas anteriores.

## Comprobar las dos copias de la interfaz

Desde la raíz:

```bash
python tools/sincronizar_frontend.py --comprobar
```

Si hay diferencias porque se ha editado `docs/`, sincronizar primero:

```bash
python tools/sincronizar_frontend.py
```

`docs/` es la fuente editable. Su copia en `Form/formulario/static/` permite que Render sirva el mismo diseño.

## Ejecutar los escenarios DOM

Requisitos: Node.js 18 o superior, npm y Python disponible. La ejecución entregada usó Node.js 24.22.1, JSDOM 26.1.0 y Python 3.12.14. La suite consulta `validators.py` con Python para comparar los mismos ejemplos de correo en el cliente y en el servidor.

Desde la raíz del repositorio:

```bash
cd pruebas_redisenio
npm ci
npm test
```

Se generan `resultados/dom_resultado.json` y `resultados/dom_pruebas.log`. Si Python no se encuentra como `python3` en Linux/macOS o como `python` en Windows, establecer la variable `PYTHON` con el ejecutable correspondiente.

Resultado de referencia de la preparación de esta entrega: 22 casos Python y 18 escenarios JSDOM aprobados. Esto no equivale a haber desplegado el proyecto en las cuentas de GitHub o Render ni a haber ejecutado Chromium.

## Capturas opcionales en un navegador real

`capturar_navegador.cjs` se entrega como herramienta para ejecutar en un equipo compatible. En la preparación del paquete solo se comprobó su sintaxis; **no se ejecutó Chromium**, por lo que el script no es una evidencia de capturas ya realizadas.

Después de `npm ci`, ejecutar desde `pruebas_redisenio/`:

```bash
npx playwright install chromium
npm run capturas
```

El script inicia un servidor local con un puerto libre y una base temporal. Abre la aplicación en modo prototipo, usa datos ficticios y guarda seis imágenes: inicio, formulario, error, confirmación y dos vistas móviles. También registra fecha y versión del navegador en `capturas_navegador/capturas_resultado.json`. No abre la cuenta de Render ni utiliza su API pública.

Si el sistema impide iniciar Chromium, se pueden tomar manualmente esas cuatro pantallas desde el navegador del equipo. Las capturas deben revisarse antes de incorporarlas al documento. No cambiar las restricciones de seguridad del equipo para ejecutar este script.

## GitHub Actions

El archivo activo `.github/workflows/pruebas-la-salle.yml` ejecuta:

1. Las 22 pruebas Python con base temporal.
2. La igualdad de las copias del frontend.
3. La instalación de las herramientas Node.
4. Los 18 escenarios DOM y la publicación de sus resultados como un artefacto del workflow.

Se activa por cambios relevantes en `main`, por pull requests y mediante ejecución manual. No ejecuta capturas de navegador ni publica el proyecto en Render por sí mismo. El despliegue de Render y GitHub Pages se configura por separado según la guía de entrega.

## Pruebas anteriores

La carpeta `pruebas/` procede de una actividad previa y conserva sus scripts como referencia histórica. Su evaluador compara hashes y selectores de la interfaz anterior; no debe usarse para juzgar el rediseño. El workflow antiguo está conservado en `pruebas/historico/pruebas-la-salle-original.yml`, fuera de `.github/workflows/`, por lo que GitHub no lo ejecuta automáticamente.
