"""Copia la interfaz de GitHub Pages al servidor de Render, o comprueba su igualdad.

Uso desde la raíz del repositorio:
    python tools/sincronizar_frontend.py
    python tools/sincronizar_frontend.py --comprobar

La fuente editable está en docs/. Nunca se necesitan cambios manuales duplicados.
Solo se copian los recursos de la aplicación; no se borran otros archivos.
"""
from pathlib import Path
import argparse
import shutil
import sys

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "docs"
DESTINO = RAIZ / "Form" / "formulario" / "static"
ARCHIVOS = ["index.html", "styles.css", "app.js", "config.js", "assets/favicon.svg"]


def main():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--comprobar", action="store_true")
    opciones = argumentos.parse_args()
    diferencias = []
    for nombre in ARCHIVOS:
        fuente = ORIGEN / nombre
        copia = DESTINO / nombre
        if not fuente.is_file():
            diferencias.append(f"Falta el archivo fuente {nombre}")
            continue
        if opciones.comprobar:
            if not copia.is_file() or fuente.read_bytes() != copia.read_bytes():
                diferencias.append(nombre)
        else:
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fuente, copia)
    if diferencias:
        print("Archivos pendientes de sincronizar: " + ", ".join(diferencias))
        return 1
    print("Interfaz sincronizada: " + str(len(ARCHIVOS)) + " archivos idénticos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
