# Despliegue de demostración

El proyecto está listo para ejecutarse en un servicio compatible con Python y variables de entorno.

## Render

1. Crear un repositorio con el contenido de la carpeta `formulario_lasalle`.
2. Crear un nuevo Web Service en Render conectado al repositorio.
3. Usar `python app.py` como comando de inicio.
4. Configurar `APP_ENV=production` y `HOST=0.0.0.0`.
5. El puerto se toma automáticamente de la variable `PORT` que entrega el proveedor.
6. Copiar la URL pública generada por Render al informe antes de la entrega académica.

El archivo `render.yaml` ya contiene la configuración básica de despliegue y no incluye secretos.
