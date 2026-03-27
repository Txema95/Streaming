#cambiamos el num de decimales para permitir las puntuaciones 10.0
ALTER TABLE contents MODIFY COLUMN vote_average DECIMAL(4,2);

#subir el tamaño máximo de paquete para permitir la inserción de datos más grandes, como descripciones largas o imágenes codificadas en base64
SET GLOBAL max_allowed_packet=67108864; -- Esto lo sube a 64MB

#añadir columna video que faltaba en el DDL original
ALTER TABLE contents ADD COLUMN video BOOLEAN DEFAULT FALSE AFTER title;