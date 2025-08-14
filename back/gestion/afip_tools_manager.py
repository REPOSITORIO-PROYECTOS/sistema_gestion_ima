# back/gestion/afip_tools_manager.py

import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Importamos la configuración y el cliente que ya tienes listos
from back import config
from back.cliente_boveda import ClienteBoveda

# Ruta al directorio seguro en el servidor de la API principal para guardado temporal
BOVEDA_TEMPORAL_PATH = "./boveda_afip_temporal"

def generar_csr_y_guardar_clave_temporal(cuit_empresa: str, razon_social: str) -> str:
    """
    Genera un par de claves. Guarda la clave privada en un archivo temporal
    seguro (.key) y devuelve el contenido del CSR para que el usuario lo descargue.
    """
    # 1. Asegurarse de que el directorio temporal exista
    os.makedirs(BOVEDA_TEMPORAL_PATH, exist_ok=True)
    
    # 2. Generar la Clave Privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')

    # 3. Guardar la clave privada en un archivo nombrado con el CUIT.
    #    Esto reemplaza el diccionario TEMP_KEY_STORAGE y es seguro para múltiples workers.
    clave_privada_path = os.path.join(BOVEDA_TEMPORAL_PATH, f"{cuit_empresa}.key")
    with open(clave_privada_path, "w") as f:
        f.write(private_key_pem)

    # 4. Construir el CSR (tu lógica original es perfecta)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"AR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, razon_social),
        x509.NameAttribute(NameOID.COMMON_NAME, cuit_empresa), # Puedes personalizar esto
        x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CUIT {cuit_empresa}")
    ])
    
    builder = x509.CertificateSigningRequestBuilder()
    csr = builder.subject_name(subject).sign(private_key, hashes.SHA256())
    
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    
    print(f"Clave privada para {cuit_empresa} guardada temporalmente en archivo. CSR listo.")
    return csr_pem

def enviar_credenciales_a_boveda(cuit: str, certificado_pem: str) -> dict:
    """
    Lee la clave privada desde el archivo temporal y envía ambas credenciales
    al microservicio de Bóveda para su almacenamiento seguro y definitivo.
    """
    clave_privada_path = os.path.join(BOVEDA_TEMPORAL_PATH, f"{cuit}.key")

    # 1. Validar que la clave temporal exista antes de continuar
    if not os.path.exists(clave_privada_path):
        raise ValueError(f"No se encontró una clave privada temporal para el CUIT {cuit}. Por favor, genere el CSR primero.")

    # 2. Leer el contenido de la clave privada temporal del disco
    with open(clave_privada_path, "r") as f:
        clave_privada_pem = f.read()

    # 3. Inicializar el cliente de la bóveda con la config que ya tienes lista
    cliente_boveda = ClienteBoveda(
        base_url=config.URL_BOVEDA,
        api_key=config.API_KEY_INTERNA
    )

    # 4. Usar el cliente para guardar el secreto en el microservicio.
    #    El cliente ya está programado para manejar los errores (403, 404, 409, etc).
    resultado_boveda = cliente_boveda.guardar_secreto(
        cuit=cuit,
        certificado=certificado_pem,
        clave_privada=clave_privada_pem
    )

    # 5. Limpieza: Si el guardado en la bóveda fue exitoso, eliminamos el archivo temporal.
    os.remove(clave_privada_path)
    print(f"Credenciales para {cuit} enviadas a la bóveda. Clave temporal eliminada.")
    
    return resultado_boveda