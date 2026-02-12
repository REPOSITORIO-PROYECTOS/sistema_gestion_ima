-- Migración: Agregar CASCADE DELETE a articulo_codigos
-- Fecha: 2026-02-12
-- Descripción: Modifica la foreign key de articulo_codigos.id_articulo 
--              para agregar ON DELETE CASCADE, permitiendo que los códigos
--              se eliminen automáticamente cuando se elimina un artículo.

-- Primero eliminar la foreign key existente
ALTER TABLE articulo_codigos 
DROP FOREIGN KEY articulo_codigos_ibfk_1;

-- Recrear la foreign key con ON DELETE CASCADE
ALTER TABLE articulo_codigos
ADD CONSTRAINT articulo_codigos_ibfk_1 
FOREIGN KEY (id_articulo) 
REFERENCES articulos(id) 
ON DELETE CASCADE;
