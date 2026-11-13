"""Entrada compatible con el nombre de pruebas de la versión anterior.

La nueva suite usa una base temporal: se evita tocar contactos existentes.
Para descubrir pruebas, utilizar test_redisenio_backend.py.
"""

if __name__ == "__main__":
    import unittest
    import test_redisenio_backend
    unittest.main(module=test_redisenio_backend, verbosity=2)
