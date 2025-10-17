# test_mesas.py
# Pruebas de funcionalidad para el módulo de mesas

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from datetime import datetime, timezone
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

# --- Importaciones del Sistema ---
from back.database import get_db
from back.modelos import Usuario, Empresa, Articulo
import back.gestion.mesas_manager as mesas_manager
from back.schemas.mesa_schemas import MesaCreate, ConsumoMesaCreate, ConsumoMesaDetalleCreate

# --- Configuración para pruebas ---
# Usar SQLite en memoria para pruebas
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Crear tablas para pruebas
from back.modelos import SQLModel
SQLModel.metadata.create_all(engine)

def get_test_db():
    """Sesión de DB para pruebas."""
    with Session(engine) as session:
        yield session

def crear_datos_prueba(db: Session, empresa_suffix: str = ""):
    """Crear datos básicos para pruebas."""
    # Crear empresa de prueba
    empresa = Empresa(
        nombre_legal=f"Empresa Test{empresa_suffix}",
        nombre_fantasia="Test Corp",
        cuit=f"1234567890{empresa_suffix}",
        activa=True,
        creada_en=datetime.now(timezone.utc)
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    # Crear usuario de prueba
    usuario = Usuario(
        nombre_usuario=f"test_user{empresa_suffix}",
        password_hash="hashed_password",
        activo=True,
        creado_en=datetime.now(timezone.utc),
        id_rol=1,  # Asumir rol existente
        id_empresa=empresa.id
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    # Crear artículo de prueba
    articulo = Articulo(
        codigo_interno="TEST001",
        descripcion="Producto Test",
        precio_venta=100.0,
        tasa_iva=0.21,
        precio_costo=80.0,
        stock_actual=50.0,  # Suficiente stock
        ubicacion="Estante A1",  # Campo requerido
        activo=True,
        id_empresa=empresa.id
    )
    db.add(articulo)
    db.commit()
    db.refresh(articulo)

    return empresa.id, usuario.id, articulo.id

def test_crud_mesas():
    """Prueba CRUD completo de mesas."""
    print("🧪 Probando CRUD de Mesas...")

    with Session(engine) as db:
        id_empresa, _, _ = crear_datos_prueba(db, "1")

        # Crear mesa
        mesa_data = MesaCreate(numero=1, capacidad=4, estado="LIBRE")
        mesa = mesas_manager.crear_mesa(db, mesa_data, id_empresa)
        print(f"✅ Mesa creada: ID={mesa.id}, Número={mesa.numero}")

        # Obtener mesa
        mesa_obtenida = mesas_manager.obtener_mesa_por_id(db, mesa.id, id_empresa)
        assert mesa_obtenida is not None
        assert mesa_obtenida.numero == 1
        print("✅ Mesa obtenida correctamente")

        # Actualizar mesa
        from back.schemas.mesa_schemas import MesaUpdate
        update_data = MesaUpdate(estado="OCUPADA", capacidad=6)
        mesa_actualizada = mesas_manager.actualizar_mesa(db, mesa.id, id_empresa, update_data)
        assert mesa_actualizada.estado == "OCUPADA"
        assert mesa_actualizada.capacidad == 6
        print("✅ Mesa actualizada correctamente")

        # Listar mesas
        mesas = mesas_manager.obtener_mesas_por_empresa(db, id_empresa)
        assert len(mesas) == 1
        print("✅ Mesas listadas correctamente")

        # Eliminar mesa
        success = mesas_manager.eliminar_mesa(db, mesa.id, id_empresa)
        assert success
        mesa_eliminada = mesas_manager.obtener_mesa_por_id(db, mesa.id, id_empresa)
        assert mesa_eliminada.activo == False
        print("✅ Mesa eliminada correctamente")

def test_consumos_mesa():
    """Prueba gestión de consumos en mesas."""
    print("🧪 Probando Consumos en Mesas...")

    with Session(engine) as db:
        id_empresa, id_usuario, id_articulo = crear_datos_prueba(db, "2")

        # Crear mesa
        mesa_data = MesaCreate(numero=1, capacidad=4, estado="LIBRE")
        mesa = mesas_manager.crear_mesa(db, mesa_data, id_empresa)

        # Crear consumo
        consumo_data = ConsumoMesaCreate(id_mesa=mesa.id)
        consumo = mesas_manager.crear_consumo_mesa(db, consumo_data, id_usuario, id_empresa)
        print(f"✅ Consumo creado: ID={consumo.id}, Mesa={consumo.id_mesa}")

        # Agregar detalle
        detalle_data = ConsumoMesaDetalleCreate(
            cantidad=2.0,
            precio_unitario=100.0,
            descuento_aplicado=0.0,
            id_articulo=id_articulo
        )
        detalle = mesas_manager.agregar_detalle_consumo(db, consumo.id, detalle_data, id_empresa)
        assert detalle is not None
        print(f"✅ Detalle agregado: Cantidad={detalle.cantidad}, Subtotal={detalle.cantidad * detalle.precio_unitario}")

        # Verificar que el stock se haya descontado
        articulo_actualizado = db.get(Articulo, id_articulo)
        assert articulo_actualizado.stock_actual == 48.0  # 50.0 - 2.0
        print(f"✅ Stock descontado correctamente: {articulo_actualizado.stock_actual}")

        # Cerrar consumo
        consumo_cerrado = mesas_manager.cerrar_consumo_mesa(db, consumo.id, id_empresa)
        assert consumo_cerrado.estado == "CERRADO"
        assert consumo_cerrado.timestamp_cierre is not None
        print("✅ Consumo cerrado correctamente")

        # Facturar consumo
        consumo_facturado = mesas_manager.facturar_consumo_mesa(db, consumo.id, id_empresa)
        assert consumo_facturado.estado == "FACTURADO"
        print("✅ Consumo facturado correctamente")

def test_ticket_consumo():
    """Prueba generación de ticket."""
    print("🧪 Probando Generación de Ticket...")

    with Session(engine) as db:
        id_empresa, id_usuario, id_articulo = crear_datos_prueba(db, "3")

        # Crear mesa y consumo con detalle
        mesa_data = MesaCreate(numero=1, capacidad=4, estado="LIBRE")
        mesa = mesas_manager.crear_mesa(db, mesa_data, id_empresa)

        consumo_data = ConsumoMesaCreate(id_mesa=mesa.id)
        consumo = mesas_manager.crear_consumo_mesa(db, consumo_data, id_usuario, id_empresa)

        detalle_data = ConsumoMesaDetalleCreate(
            cantidad=1.0,
            precio_unitario=150.0,
            descuento_aplicado=10.0,
            id_articulo=id_articulo
        )
        mesas_manager.agregar_detalle_consumo(db, consumo.id, detalle_data, id_empresa)

        # Generar ticket
        ticket_data = mesas_manager.generar_ticket_consumo(db, consumo.id, id_empresa)
        assert ticket_data is not None
        assert ticket_data["mesa_numero"] == 1
        assert len(ticket_data["detalles"]) == 1
        assert ticket_data["total"] == 140.0  # 150 - 10 descuento
        print("✅ Ticket generado correctamente")
        print(f"   Mesa: {ticket_data['mesa_numero']}")
        print(f"   Total: ${ticket_data['total']}")
        print(f"   Items: {len(ticket_data['detalles'])}")

def run_all_tests():
    """Ejecutar todas las pruebas."""
    print("🚀 Iniciando pruebas del módulo de Mesas\n")

    try:
        test_crud_mesas()
        print()
        test_consumos_mesa()
        print()
        test_ticket_consumo()
        print("\n🎉 Todas las pruebas pasaron exitosamente!")

    except Exception as e:
        print(f"\n❌ Error en las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()