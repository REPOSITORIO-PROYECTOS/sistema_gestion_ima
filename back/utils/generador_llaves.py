# back/utils/generador_llaves.py
import random
import datetime

# --- EL DICCIONARIO ---
# Una lista simple de palabras. Puedes ampliarla enormemente.
# Para mayor seguridad, estas listas podrían estar en un archivo de configuración.
ADJETIVOS = ["rojo", "azul", "verde", "grande", "pequeño", "rapido", "lento", "brillante", "oscuro"]
SUSTANTIVOS = ["sol", "luna", "rio", "montaña", "arbol", "casa", "perro", "gato", "cielo"]
VERBOS = ["corre", "salta", "vuela", "nada", "crece", "brilla", "duerme", "come", "mira"]

def generar_nueva_llave() -> str:
    """
    Crea una nueva llave maestra combinando palabras aleatorias y un número.
    Ejemplo: 'rapido-luna-brilla-88'
    """
    palabra1 = random.choice(ADJETIVOS + SUSTANTIVOS + VERBOS)
    numero = random.randint(10, 99)
    
    llave = f"{palabra1}{numero}"
    return llave