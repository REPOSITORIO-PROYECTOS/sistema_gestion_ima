# back/gestion/empresa_manager.py

from sqlmodel import Session, select
from typing import List

from back.modelos import Empresa, ConfiguracionEmpresa, Usuario, Rol
from back.schemas.empresa_schemas import EmpresaCreate
from back.schemas.admin_schemas import UsuarioCreate # <-- ¡IMPORTANTE! Importamos el schema que usa admin_manager

# --- ¡COLABORACIÓN ENTRE MANAGERS! ---
# Importamos el manager de administración para reutilizar su lógica
import back.gestion.admin.admin_manager as admin_manager

def crear_empresa_y_primer_admin(db: Session, data: EmpresaCreate) -> Empresa:
    """
    Crea una nueva Empresa y su primer Usuario Administrador en una única
    transacción atómica. REUTILIZA la lógica de `admin_manager.crear_usuario`.
    """
    print(f"\n--- [TRACE: CREAR EMPRESA Y ADMIN (Reutilizando Lógica)] ---")
    print(f"1. Solicitud para CUIT: {data.cuit}, Admin: {data.admin_username}")

    # --- INICIO DE LA TRANSACCIÓN ---
    # 1. Validaciones de unicidad (CUIT, Nombre Legal)
    if db.exec(select(Empresa).where(Empresa.cuit == data.cuit)).first():
        raise ValueError(f"El CUIT '{data.cuit}' ya está registrado.")
    if db.exec(select(Empresa).where(Empresa.nombre_legal == data.nombre_legal)).first():
        raise ValueError(f"El nombre legal '{data.nombre_legal}' ya está registrado.")
    
    # El admin_manager ya valida la unicidad del username, no necesitamos repetirlo.
    print("2. Validaciones de empresa superadas.")

    try:
        # 3. Crear la Empresa y su Configuración (sin commit todavía)
        nueva_empresa = Empresa(
            nombre_legal=data.nombre_legal,
            nombre_fantasia=data.nombre_fantasia,
            cuit=data.cuit
        )
        db.add(nueva_empresa)
        
        configuracion_inicial = ConfiguracionEmpresa(
            empresa=nueva_empresa,
            link_google_sheets=data.link_google_sheets
        )
        db.add(configuracion_inicial)
        
        # Hacemos un "flush" para que nueva_empresa obtenga un ID provisional
        # que podamos usar para el nuevo usuario, sin cerrar la transacción.
        print("3. Pre-registrando empresa para obtener su ID...")
        db.flush()

        # 4. Preparar los datos para llamar al `admin_manager.crear_usuario`
        # Asumimos que el rol para el admin de una empresa es "Admin" (o el que corresponda)
        rol_admin = db.exec(select(Rol).where(Rol.nombre == "Admin")).first()
        if not rol_admin:
            raise RuntimeError("El rol 'Admin' no se encuentra en la base de datos.")

        datos_nuevo_usuario = UsuarioCreate(
            nombre_usuario=data.admin_username,
            password=data.admin_password,
            id_rol=rol_admin.id,
            id_empresa=nueva_empresa.id # <-- ¡Le pasamos el ID de la empresa recién creada!
        )
        
        # 5. Llamar a la función existente para crear el usuario
        print(f"4. Reutilizando 'admin_manager.crear_usuario' para el usuario '{data.admin_username}'...")
        admin_manager.crear_usuario(db, datos_nuevo_usuario, commit_transaction=False)
        
        # 6. Si todo ha ido bien, hacemos el commit final
        print("5. Todas las operaciones exitosas. Realizando commit final...")
        db.commit()
        db.refresh(nueva_empresa)
        print(f"   -> ¡ÉXITO! Empresa ID: {nueva_empresa.id} y su admin han sido creados atómicamente.")
        
    except Exception as e:
        print(f"   -> ERROR durante la transacción: {e}")
        db.rollback() # ¡CRÍTICO! Si algo falla, se revierte todo.
        # Re-lanzamos el error para que el router lo capture.
        raise e

    print("--- [FIN TRACE] ---\n")
    return nueva_empresa

def obtener_todas_las_empresas(db: Session, incluir_inactivas: bool = False) -> List[Empresa]:
    """ Devuelve una lista de empresas. """
    statement = select(Empresa).order_by(Empresa.nombre_legal)
    if not incluir_inactivas:
        statement = statement.where(Empresa.activa == True)
    return db.exec(statement).all()