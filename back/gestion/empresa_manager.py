# back/gestion/empresa_manager.py
# Lógica de negocio para la gestión de Empresas (clientes del sistema)

from sqlmodel import Session, select
from typing import Optional, List

# --- Módulos del Proyecto ---
from back.modelos import Empresa, ConfiguracionEmpresa
from back.schemas.empresa_schemas import EmpresaCreate # Asumimos que este schema existe

# ===================================================================
# === LÓGICA DE GESTIÓN DE EMPRESAS
# ===================================================================

def crear_empresa(db: Session, empresa_data: EmpresaCreate) -> Empresa:
    """
    Crea una nueva empresa en el sistema.
    Verifica que el CUIT y el nombre legal no estén ya en uso.
    Automáticamente crea un registro de configuración por defecto para la nueva empresa.
    """
    print(f"\n--- [TRACE: CREAR EMPRESA] ---")
    print(f"1. Solicitud para crear empresa con CUIT: {empresa_data.cuit}")

    # 1. Verificar que el CUIT no esté duplicado
    statement_cuit = select(Empresa).where(Empresa.cuit == empresa_data.cuit)
    if db.exec(statement_cuit).first():
        raise ValueError(f"El CUIT '{empresa_data.cuit}' ya está registrado en el sistema.")

    # 2. Verificar que el nombre legal no esté duplicado
    statement_nombre = select(Empresa).where(Empresa.nombre_legal == empresa_data.nombre_legal)
    if db.exec(statement_nombre).first():
        raise ValueError(f"El nombre legal '{empresa_data.nombre_legal}' ya está registrado.")
    
    print("2. Validaciones de unicidad superadas.")

    # 3. Crear la nueva empresa
    nueva_empresa = Empresa(
        nombre_legal=empresa_data.nombre_legal,
        nombre_fantasia=empresa_data.nombre_fantasia,
        cuit=empresa_data.cuit
    )
    
    # 4. Crear su configuración por defecto asociada
    # El modelo ConfiguracionEmpresa espera un objeto Empresa para la relación
    configuracion_por_defecto = ConfiguracionEmpresa(empresa=nueva_empresa)
    
    try:
        db.add(nueva_empresa)
        db.add(configuracion_por_defecto)
        print("3. Intentando registrar la nueva empresa y su configuración en la base de datos...")
        db.commit()
        db.refresh(nueva_empresa)
        print(f"   -> ¡ÉXITO! Empresa registrada con ID: {nueva_empresa.id}")
        
    except Exception as e:
        print(f"   -> ERROR de BD al registrar la empresa: {e}")
        db.rollback()
        raise RuntimeError(f"Error de base de datos al registrar la empresa: {e}")

    print("--- [FIN TRACE] ---\n")
    return nueva_empresa


def obtener_empresa_por_id(db: Session, id_empresa: int) -> Optional[Empresa]:
    """
    Obtiene una empresa específica por su ID.
    """
    return db.get(Empresa, id_empresa)

def desactivar_o_reactivar_empresa(db: Session, id_empresa: int, activar: bool) -> Empresa:
    """
    Desactiva o reactiva una empresa cambiando su estado.
    """
    empresa = db.get(Empresa, id_empresa)
    if not empresa:
        raise ValueError(f"No se encontró una empresa con el ID {id_empresa}.")

    # Lógica usando tu campo 'activo' (o como se llame)
    if  empresa.activa == activar:
        estado_actual = "activa" if activar else "inactiva"
        print(f"La empresa ya se encuentra {estado_actual}. No se realizan cambios.")
        return empresa
    
    empresa.activo = activar # <-- USAMOS TU CAMPO
    
    try:
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        return empresa
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Error de base de datos: {e}")

def obtener_todas_las_empresas(db: Session, incluir_inactivas: bool = False) -> List[Empresa]:
    """
    Devuelve una lista de empresas.
    """
    statement = select(Empresa).order_by(Empresa.nombre_legal)
    if not incluir_inactivas:
        # Filtramos usando tu campo
        statement = statement.where(Empresa.activa == True) # <-- USAMOS TU CAMPO
    return db.exec(statement).all()