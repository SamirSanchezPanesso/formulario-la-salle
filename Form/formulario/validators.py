import re

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def validate_contact(data):
    fields = ["name", "email", "subject", "message"]
    errors = {}
    for field in fields:
        value = str(data.get(field, "")).strip()
        if not value:
            errors[field] = "Este campo es obligatorio."
    email = str(data.get("email", "")).strip()
    if email and not EMAIL_PATTERN.fullmatch(email):
        errors["email"] = "Ingresa un correo electrónico válido."
    return errors
