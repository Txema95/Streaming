-- 1. Tabla Maestra de Contenido (Películas y Series)
CREATE TABLE contents (
    tmdb_id INT PRIMARY KEY,
    content_type ENUM('movie', 'tv') NOT NULL,
    title VARCHAR(255) NOT NULL, -- Mapea 'title' (movie) y 'name' (tv)
    original_title VARCHAR(255),
    overview TEXT,
    release_date DATE,           -- Mapea 'release_date' y 'first_air_date'
    original_language VARCHAR(10),
    popularity DECIMAL(10,3),
    poster_path VARCHAR(255),
    backdrop_path VARCHAR(255),
    vote_average DECIMAL(4,2),
    vote_count INT,
    adult BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Géneros (Catálogo estático de TMDB)
CREATE TABLE genres (
    id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- 3. Relación Muchos a Muchos (Un contenido puede tener varios géneros)
CREATE TABLE content_genres (
    content_id INT,
    genre_id INT,
    PRIMARY KEY (content_id, genre_id),
    FOREIGN KEY (content_id) REFERENCES contents(tmdb_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- 4. Tabla Unificada de Estadísticas
CREATE TABLE content_stats (
    content_id INT PRIMARY KEY,
    certificacion VARCHAR(10),
    espectadores_live INT DEFAULT 0,
    reproducciones_totales INT DEFAULT 0,
    es_tendencia BOOLEAN DEFAULT FALSE,
    es_popular BOOLEAN DEFAULT FALSE,
    es_historico_vistas BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (content_id) REFERENCES contents(tmdb_id) ON DELETE CASCADE
);

-- 5. Tabla de Usuarios
CREATE TABLE users (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    passwd VARCHAR(255) NOT NULL, -- Recuerda guardar hashes, no texto plano
    fecha_nacimiento DATE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);