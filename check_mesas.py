import sys
import os
sys.path.append(os.path.dirname(__file__))

from back.database import get_db
from sqlmodel import select
from back.modelos import Mesa

db = next(get_db())
mesas = db.exec(select(Mesa)).all()
print('Mesas existentes:')
for mesa in mesas:
    print(f'ID: {mesa.id}, Numero: {mesa.numero}, Empresa: {mesa.id_empresa}, Estado: {mesa.estado}, Activo: {mesa.activo}')