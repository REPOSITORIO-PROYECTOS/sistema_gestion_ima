# /sistema_gestion_ima/back/gestion/reportes/ciclo_vida_comp.py

from sqlmodel import Session, select
from fastapi import HTTPException, status
from typing import List

from back.modelos import Usuario, Venta, VentaDetalle

def agrupar_comprobantes_en_uno_nuevo(
    db: Session,
    usuario: Usuario,
    ids_a_agrupar: List[int],
    nuevo_tipo_comprobante: str
) -> Venta:
    """
    Agrupa múltiples comprobantes existentes (ej: Remitos) en uno solo nuevo (ej: Factura).
    - Consolida todos los items.
    - Crea un nuevo comprobante.
    - Anula los comprobantes originales.
    """
    print(f"--- [AGRUPACIÓN] Iniciando agrupación de {len(ids_a_agrupar)} comprobantes en un '{nuevo_tipo_comprobante}' ---")

    # 1. Validación Rigurosa
    if not ids_a_agrupar:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe proporcionar una lista de IDs de comprobantes para agrupar.")

    statement = select(Venta).where(Venta.id.in_(ids_a_agrupar), Venta.id_empresa == usuario.id_empresa)
    comprobantes = db.exec(statement).all()

    if len(comprobantes) != len(ids_a_agrupar):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uno o más comprobantes no fueron encontrados o no pertenecen a la empresa.")

    primer_comprobante = comprobantes[0]
    id_cliente = primer_comprobante.id_cliente

    for comp in comprobantes:
        if not comp.activo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El comprobante ID {comp.id} ya está anulado y no puede ser agrupado.")
        if comp.tipo_comprobante != "Remito": # Podríamos hacer esto configurable
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Solo se pueden agrupar comprobantes de tipo 'Remito'. Se encontró un '{comp.tipo_comprobante}'.")
        if comp.id_cliente != id_cliente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todos los comprobantes deben pertenecer al mismo cliente.")

    # 2. Consolidación de Items y Cálculo de Total
    items_consolidados = []
    total_consolidado = 0.0

    for comp in comprobantes:
        for item in comp.items:
            # Creamos una nueva instancia de VentaDetalle, no la movemos.
            nuevo_detalle = VentaDetalle(
                id_articulo=item.id_articulo,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario
            )
            items_consolidados.append(nuevo_detalle)
            total_consolidado += item.cantidad * item.precio_unitario
    
    print(f"--- [AGRUPACIÓN] {len(items_consolidados)} items consolidados. Total: {total_consolidado} ---")

    # 3. Creación del Nuevo Comprobante Agrupador
    comprobante_final = Venta(
        total=total_consolidado,
        tipo_comprobante=nuevo_tipo_comprobante,
        activo=True,
        id_cliente=id_cliente,
        id_usuario=usuario.id,
        id_empresa=usuario.id_empresa,
        items=items_consolidados # Asociamos la lista de nuevos detalles
    )
    db.add(comprobante_final)

    # 4. Anulación de los Comprobantes Originales
    print(f"--- [AGRUPACIÓN] Anulando {len(comprobantes)} comprobantes originales... ---")
    for comp in comprobantes:
        comp.activo = False
        # Podríamos añadir una nota, si el modelo Venta tuviera un campo para ello.
        # comp.notas = f"Agrupado en Venta ID: {comprobante_final.id}" 
        db.add(comp)
        
    # La sesión que llama a esta función se encargará del commit.
    
    return comprobante_final