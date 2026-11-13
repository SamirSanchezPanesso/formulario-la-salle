"""Reglas compartidas por todas las solicitudes de contacto del servidor."""

import re

# Validación práctica de formato. No comprueba si la dirección existe ni
# si una persona puede recibir correo en ella.
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$"
)

FIELD_LIMITS = {
    "name": (2, 100),
    "email": (3, 254),
    "subject": (3, 120),
    "message": (10, 2000),
}


def validate_contact(data):
    """Devuelve errores por campo; no convierte tipos ni modifica la entrada.

    Los nombres de las claves conservan el contrato de la versión original.
    Un null, un número o una lista no son textos válidos. Primero se comprueba
    el tipo para impedir que una entrada inválida llegue al almacenamiento.
    """
    if not isinstance(data, dict):
        return {"form": "El contenido debe ser un objeto JSON."}

    errores = {}
    for campo, (minimo, maximo) in FIELD_LIMITS.items():
        valor = data.get(campo, "")
        if not isinstance(valor, str):
            errores[campo] = "Este campo debe ser texto."
            continue
        valor = valor.strip()
        if not valor:
            errores[campo] = "Este campo es obligatorio."
        elif len(valor) < minimo:
            errores[campo] = f"Escribe al menos {minimo} caracteres."
        elif len(valor) > maximo:
            errores[campo] = f"Escribe como máximo {maximo} caracteres."

    correo = data.get("email")
    if isinstance(correo, str) and "email" not in errores:
        correo = correo.strip()
        parte_local = correo.rpartition("@")[0]
        if (
            not EMAIL_PATTERN.fullmatch(correo)
            or len(parte_local) > 64
            or parte_local.startswith(".")
            or parte_local.endswith(".")
            or ".." in parte_local
        ):
            errores["email"] = "Ingresa un correo electrónico válido."
    return errores
