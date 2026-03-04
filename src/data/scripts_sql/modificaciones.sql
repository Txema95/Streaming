#cambiamos el num de decimales para permitir las puntuaciones 10.0
ALTER TABLE contents MODIFY COLUMN vote_average DECIMAL(4,2);