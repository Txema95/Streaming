######################################################################################

# Descripción del Ejercicio

#######################################################################################

Un magnate de dubai quiere hacer su propia plataforma de peliculas y series, quiere todo lo que hay en el mundo quitandando lo inmoral.

## Que tenemos

1. Datos disponibles
   1. Datos de peliculas
   2. Datos de serie

2. interfaz inicial y qué le podemos pedir al usuario
   1. Catalogo predeterminado
      - Los 10 mas vistos con search_similarity
        - un top 3 con experto
      - Top 5 mejor puntuado por todos en la plataforma
        ....
   2. Filtro usuario
      - Genero
      - Fecha
      - idioma
      - random --> Ruleta o maquina tragaperras

   3. Al crear el usuario selecciona si quiere definir sus gustos o lo omite
      - Parametros del gusto del usuario:
        - Genero : terror, amor, suspense, accion
        - Tipo : Normal , dibujos , anime

## Cuál es el flujo

1. INPUTS
   1. Acceso del usuario --> pasa su ID --> Ver si ya tiene datos de gustos
   2. Selector del filtro

2. Esto va a una DB
   1. Consulta los datos de las peliculas y series
   2. Saca los datos necesarios.
3. Vectorizados la información
4. Inferencia del modelo.
5. MOSTRAMOS RESUTLADOS

## Qué restricciones sabemos que tenemos con nuestra información actual

1. Usuario nuevo --> falta completa de datos --> Aleatorio y filtros o seleccion del usuario por fijar parametros al crear la cuenta.

2.

## PREPARACIÓM DB

Descargar mysql server y workbench
https://dev.mysql.com/downloads/installer/

configurar mysql server
usuario: txema
contraseña: root
contraseña_root: root

añadir mysql al path:

- editar variables de entorno
- editar path
- añadir al final:
  C:\Program Files\MySQL\MySQL Server 8.0\bin

desde consola ejecutar y escribir contraseña de root definida en la instalación:
mysql -u root -p

creamos la base de datos:
CREATE DATABASE streaming_db;

desde el workbench ejecutar el script
src\data\scripts_sql\create_database.sql

CONECTAR A BBDD LOCAL

- instalar conector:
  pip install mysql-connector-python

## PREPARACIÓN BACKEND

Usamos fastapi para montar un backend
pip install fastapi uvicorn requests

## PREPARACIÓN FRONTEND

Usamos streamlit
pip install streamlit

## Configurar .env

pip install dotenv

## VECTORIZACIÓN

## MODELO
