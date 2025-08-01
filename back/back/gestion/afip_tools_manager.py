# back/gestion/afip_tools_manager.py

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Un almacenamiento temporal simple para la clave privada.
# ¡ADVERTENCIA! Esto es solo para un único worker. En producción con múltiples
# workers/servidores, se debe usar un almacenamiento compartido como Redis o una tabla temporal en la DB.
TEMP_KEY_STORAGE = {}

def generar_claves_y_csr(cuit_empresa: str, razon_social: str) -> (str, str):
    """
    Genera una nueva clave privada y un CSR para AFIP.

    Retorna:
        - El contenido de la Clave Privada (para guardar temporalmente).
        - El contenido del CSR (para enviar al usuario).
    """
    # 1. Generar la Clave Privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')

    # 2. Construir el CSR
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"AR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, razon_social.encode('utf-8').decode('latin-1')),
        x509.NameAttribute(NameOID.COMMON_NAME, u"Sistema Gestion IMA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CUIT {cuit_empresa}")
    ])
    
    builder = x509.CertificateSigningRequestBuilder()
    csr = builder.subject_name(subject).sign(private_key, hashes.SHA256())
    
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    # 3. Guardar la clave privada temporalmente
    # Usamos el CUIT como identificador único para esta sesión.
    TEMP_KEY_STORAGE[cuit_empresa] = private_key_pem
    
    print(f"Claves generadas para CUIT {cuit_empresa}. CSR listo para descargar.")

    return private_key_pem, csr_pem

# Aquí necesitaríamos la lógica que llama al microservicio Bóveda.
# def guardar_credenciales_en_boveda(cuit: str, cert_pem: str, key_pem: str):
#     # Lógica para llamar a POST /secrets/{cuit}/afip_cert y POST /secrets/{cuit}/afip_key
#     # ...
#     pass