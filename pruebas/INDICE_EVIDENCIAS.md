# Índice verificable de pruebas y evidencias

Seis pruebas ejecutadas el 26-10-2026 sobre dos copias **locales**: versión original (baseline) y versión con dos correcciones (corregido). Los registros no demuestran cambios en Render.

## Resumen de los casos

| ID | Nivel | Comportamiento | Original | Corregido | Evidencias |
|:--|:--|:--|:--|:--|:--|
| U01 | Unitario | Entradas de texto válidas | APROBADO | APROBADO | [Original](evidencias/baseline/U01.json) · [Corregido](evidencias/corregido/U01.json) |
| U02 | Unitario | Nombre nulo en la función | FALLIDO | APROBADO | [Original](evidencias/baseline/U02.json) · [Corregido](evidencias/corregido/U02.json) |
| I01 | Integración | HTTP 201 y persistencia SQLite | APROBADO | APROBADO | [Original](evidencias/baseline/I01.json) · [Corregido](evidencias/corregido/I01.json) |
| I02 | Integración | Nombre nulo en la API | FALLIDO | APROBADO | [Original](evidencias/baseline/I02.json) · [Corregido](evidencias/corregido/I02.json) |
| F01 | Funcional | Carga de recursos y envío desde / | FALLIDO | APROBADO | [Original](evidencias/baseline/F01.json) · [Corregido](evidencias/corregido/F01.json) |
| F02 | Funcional | Correo inválido y mensaje visible | APROBADO | APROBADO | [Original](evidencias/baseline/F02.json) · [Corregido](evidencias/corregido/F02.json) |

**Resultado agregado:** original 3/6 aprobados; corregido 6/6 aprobados. Dos causas raíz: validación de `null` y rutas relativas del CSS/JS.

## Código automatizado y herramientas

- [Cuatro pruebas unitarias / integración en Python (`unittest`)](tests_backend.py)
- [Dos pruebas funcionales en Playwright/Chromium](tests_funcionales.cjs)
- [Ejecutor y generación de nuevas evidencias](reproducir.py)
- [Servidor local aislado](server_local.py)
- [Dependencias JavaScript](package.json)
- [Versión exacta del ejecutor utilizado para las evidencias archivadas](historico/reproducir_v1.py)

## Registros de ejecución y defectos

- [Manifiesto JSON global con entorno, hashes y resultados](evidencias/resumen.json)
- [Log unittest original](evidencias/baseline/unittest.log) · [log corregido](evidencias/corregido/unittest.log)
- [Log navegador original](evidencias/baseline/funcional.log) · [log corregido](evidencias/corregido/funcional.log)
- [Log de servidor original](evidencias/baseline/servidor.log) · [log corregido](evidencias/corregido/servidor.log)
- [Parche revisable de los dos defectos](evidencias/correcciones.patch)
- [Lectura en texto de todos los estados](evidencias/lectura_resultados.txt)

## Alcance y trazabilidad

- Datos ficticios; HTTP real local, SQLite temporal y Chromium real.
- El manifiesto histórico conserva el hash del ejecutor v1; se encuentra íntegro en `historico/`.
- El ejecutor principal ahora verifica los hashes de la aplicación en lugar de exigir que `HEAD` sea el commit antiguo.
- Si los archivos de `Form/formulario/` cambian respecto a la referencia histórica, el ejecutor se detiene antes de dar resultados engañosos.
- Los resultados corregidos pertenecen a una **copia temporal**; publicar esta carpeta no instala las correcciones en producción.

Enlace directo al repositorio (después de subir esta carpeta): https://github.com/SamirSanchezPanesso/formulario-la-salle/tree/main/pruebas
