# Carpeta histórica de una actividad anterior

Los scripts de esta carpeta se conservan como referencia de las pruebas realizadas sobre la interfaz anterior. No son la suite vigente del rediseño.

`reproducir.py` comprueba hashes de una versión antigua y compara escenarios baseline/corregido. Los cambios de HTML, JavaScript y Python del rediseño hacen que esa comprobación no corresponda al código actual. No cambiar los hashes para aparentar que la versión anterior y la actual son iguales.

El workflow anterior se conserva en `historico/pruebas-la-salle-original.yml`; al estar fuera de `.github/workflows/`, no se ejecuta automáticamente.

Para verificar la entrega actual, consultar `../pruebas_redisenio/README.md` y ejecutar las pruebas Python y JSDOM allí indicadas. Las evidencias de actividades anteriores no se atribuyen al rediseño actual.
