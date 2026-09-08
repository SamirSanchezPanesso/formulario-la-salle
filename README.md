Desarrollo de una Aplicación Web en 3 Ambientes: 
Ambiente de desarrollo
Ambiente de pruebas
Ambiente de producción

Tecnologías:
•	Python 3: Utilizado como motor para el servidor HTTP, la API, la gestión de la configuración y la ejecución de pruebas. Su justificación radica en que permite una ejecución completamente reproducible sin depender de librerías externas complejas. 
•	HTML5, CSS3 y JavaScript: Empleados para el diseño de la interfaz de usuario, la validación visual en el cliente y el consumo asíncrono de la API. Se seleccionaron por ser tecnologías estándar en cualquier navegador web y altamente compatibles para despliegues rápidos. 
•	SQLite: Utilizada como sistema de persistencia de datos adaptado a cada ambiente de trabajo. Su principal ventaja es que provee una base de datos integrada, independiente por ambiente y que no requiere la configuración de credenciales de acceso. 
•	unittest: Framework nativo incluido en Python para la automatización de los tres casos de prueba principales, ideal para verificar respuestas HTTP de forma estándar. 

Comparación de los Ambientes de Trabajo:
El sistema adapta su comportamiento de manera dinámica mediante la variable de entorno APP_ENV, estructurándose en tres ambientes operativos diferenciados:
•	Ambiente de Desarrollo (development): Configurado para operar en el puerto local por defecto 8000. Cuenta con el modo de depuración habilitado y almacena su información en la base de datos contacts_development.db. Su objetivo principal es permitir la codificación y ejecución controlada de cambios. 
•	Ambiente de Pruebas (testing): Configurado para ejecutarse en el puerto local 8001. Mantiene la depuración habilitada orientada a la validación de componentes y utiliza la base de datos contacts_testing.db. Su propósito es la ejecución sistemática de casos de prueba. 
•	Ambiente de Producción / Demo (production): Configurado para ejecutarse en el puerto 8002 o tomar dinámicamente el puerto (PORT) asignado por el proveedor de alojamiento en la nube. En este ambiente la depuración se encuentra totalmente deshabilitada por motivos de seguridad y rendimiento, utilizando de forma aislada la base de datos contacts_production.db. 

Instrucciones de Instalación y Ejecución
•	Requisito previo: Tener instalado Python en su versión 3.10 o superior. El proyecto no requiere la instalación manual de paquetes externos adicionales. 
•	Pasos generales: Descomprima la carpeta del proyecto, abra una terminal ubicada en el directorio de la aplicación y ejecute el archivo correspondiente según su sistema operativo y el ambiente que desee levantar. 

En Sistemas operativos Windows:
•	Para iniciar en Desarrollo: Ejecute el archivo run_development.bat. 
•	Para iniciar en Pruebas: Ejecute el archivo run_testing.bat. 
•	Para iniciar en Producción: Ejecute el archivo run_production.bat. 

En Sistemas operativos Linux / macOS:
•	Para iniciar en Desarrollo: Ejecute el comando ./run_development.sh. 
•	Para iniciar en Pruebas: Ejecute el comando ./run_testing.sh. 
•	Para iniciar en Producción: Ejecute el comando ./run_production.sh. 
