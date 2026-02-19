Resumen
Este conjunto de datos (ml-latest) describe la actividad de valoración de 5 estrellas y etiquetado en texto libre de MovieLens, un servicio de recomendación de películas. Contiene 33832162 clasificaciones y aplicaciones de etiquetas 2328315 en 86.537 películas. Estos datos fueron creados por 330975 usuarios entre el 9 de enero de 1995 y el 20 de julio de 2023. Este conjunto de datos fue generado el 20 de julio de 2023.

Los usuarios fueron seleccionados al azar para su inclusión. Todos los usuarios seleccionados habían valorado al menos 1 película. No se incluye información demográfica. Cada usuario está representado por un id y no se proporciona otra información.

Los datos están contenidos en los archivos , , , , y . A continuación, más detalles sobre el contenido y el uso de todos estos archivos.genome-scores.csvgenome-tags.csvlinks.csvmovies.csvratings.csvtags.csv

Este es un conjunto de datos de desarrollo. Por tanto, puede cambiar con el tiempo y no es un conjunto de datos adecuado para resultados de investigación compartidos. Consulta los conjuntos de datos de referencia disponibles si esa es tu intención.

Este y otros conjuntos de datos de GroupLens están disponibles públicamente para su descarga en http://grouplens.org/datasets/.

Licencia de Uso
Ni la Universidad de Minnesota ni ninguno de los investigadores implicados pueden garantizar la corrección de los datos, su idoneidad para un propósito concreto o la validez de los resultados basados en el uso del conjunto de datos. El conjunto de datos puede utilizarse para cualquier propósito de investigación bajo las siguientes condiciones:

El usuario no puede declarar ni insinuar ningún respaldo de la Universidad de Minnesota ni del Grupo de Investigación GroupLens.
El usuario debe reconocer el uso del conjunto de datos en publicaciones resultante del uso del conjunto de datos (véase más abajo información de citas).
El usuario puede redistribuir el conjunto de datos, incluidas las transformaciones, siempre que se distribuya bajo estas mismas condiciones de licencia.
El usuario no puede utilizar esta información con fines comerciales o generadores de ingresos sin obtener previamente el permiso de un miembro del profesorado del Proyecto de Investigación GroupLens de la Universidad de Minnesota.
Los scripts ejecutables del software se proporcionan "tal cual" sin ninguna garantía, expresa o implícita, incluyendo, pero no limitado a, las garantías implícitas de comerciabilidad y idoneidad para un propósito particular. Todo el riesgo respecto a la calidad y el rendimiento recae en ti. Si el programa resulta defectuoso, asumes el coste de todo el mantenimiento, reparación o corrección necesaria.
En ningún caso la Universidad de Minnesota, sus afiliados o empleados serán responsables ante usted por daños derivados del uso o incapacidad para utilizar estos programas (incluyendo, pero no limitándose a, pérdida de datos o que los datos se vuelvan inexactos).

Si tienes más preguntas o comentarios, por favor envíanos un correo electrónico a grouplens-info@umn.edu

Cita
Para reconocer el uso del conjunto de datos en publicaciones, por favor cite el siguiente artículo:

F. Maxwell Harper y Joseph A. Konstan. 2015. Los conjuntos de datos de MovieLens: Historia y contexto. Transacciones ACM sobre Sistemas Inteligentes Interactivos (TiiS) 5, 4: 19:1–19:19. https://doi.org/10.1145/2827872

Más información sobre GroupLens
GroupLens es un grupo de investigación del Departamento de Informática e Ingeniería de la Universidad de Minnesota. Desde su creación en 1992, los proyectos de investigación de GroupLens han explorado una variedad de campos, entre ellos:

Sistemas de recomendación
Comunidades en línea
Tecnologías móviles y ubicuas
Bibliotecas digitales
Sistemas de información geográfica local
GroupLens Research opera un receptador de películas basado en filtrado colaborativo, MovieLens, que es la fuente de estos datos. ¡Te animamos a visitar http://movielens.org para probarlo! Si tienes ideas interesantes para trabajos experimentales para realizar en MovieLens, mándanos un correo a grouplens-info@cs.umn.edu - siempre estamos interesados en trabajar con colaboradores externos.

Contenido y uso de archivos
Formato y codificación
Los archivos de conjunto de datos se escriben como archivos de valores separados por comas con una sola fila de cabecera. Las columnas que contienen comas () se evaden usando comillas dobles (). Estos archivos están codificados como UTF-8. Si los caracteres acentuados en títulos de películas o valores de etiquetas (por ejemplo, Miserables, Les (1995)) se muestran incorrectamente, asegúrese de que cualquier programa que lea los datos, como un editor de texto, terminal o script, esté configurado para UTF-8.,"

Identificadores de usuario
Los usuarios de MovieLens fueron seleccionados al azar para su inclusión. Sus identificaciones han sido anonimizadas. Los ID de usuario son consistentes entre y (es decir, el mismo id se refiere al mismo usuario en los dos archivos).ratings.csvtags.csv

Identificaciones de películas
Solo las películas con al menos una clasificación o etiqueta están incluidas en el conjunto de datos. Estos identificadores de películas son consistentes con los usados en la web de MovieLens (por ejemplo, id corresponde a la URL https://movielens.org/movies/1). Los ids de película son consistentes entre , , , y (es decir, el mismo id se refiere a la misma película en estos cuatro archivos de datos).1ratings.csvtags.csvmovies.csvlinks.csv

Estructura del Archivo de Datos de Calificaciones (ratings.csv)
Todas las calificaciones están contenidas en el archivo. Cada línea de este archivo después de la fila de cabecera representa una valoración de una película por un usuario, y tiene el siguiente formato:ratings.csv

userId,movieId,rating,timestamp
Las líneas dentro de este archivo están ordenadas primero por userId, luego, dentro de user, por movieId.

Las valoraciones se realizan en una escala de 5 estrellas, con incrementos de media estrella (0,5 estrellas - 5,0 estrellas).

Las marcas de tiempo representan segundos desde la medianoche del Tiempo Universal Coordinado (UTC) del 1 de enero de 1970.

Etiquetas Estructura de archivos de datos (tags.csv)
Todas las etiquetas están contenidas en el archivo . Cada línea de este archivo después de la fila de encabezado representa una etiqueta aplicada a una película por un solo usuario, y tiene el siguiente formato:tags.csv

userId,movieId,tag,timestamp
Las líneas dentro de este archivo están ordenadas primero por userId, luego, dentro de user, por movieId.

Las etiquetas son metadatos generados por el usuario sobre películas. Cada etiqueta suele ser una sola palabra o frase corta. El significado, valor y propósito de una etiqueta particular lo determina cada usuario.

Las marcas de tiempo representan segundos desde la medianoche del Tiempo Universal Coordinado (UTC) del 1 de enero de 1970.

Estructura de archivos de datos de películas (movies.csv)
La información de la película está contenida en el archivo. Cada línea de este archivo después de la fila de cabecera representa una película, y tiene el siguiente formato:movies.csv

movieId,title,genres
Los títulos de las películas se introducen manualmente o se importan desde https://www.themoviedb.org/, e incluyen el año de estreno entre paréntesis. Pueden existir errores e inconsistencias en estos títulos.

Los géneros son una lista separada por pipas y se seleccionan entre los siguientes:

Acción
Aventura
Animación
Infantil
Comedia
Crimen
Documental
Drama
Fantasía
Cine negro
Terror
Musical
Misterio
Romance
Ciencia ficción
Thriller
Guerra
Oeste
(no se listan géneros)
Estructura de archivos de datos de enlaces (links.csv)
Los identificadores que pueden usarse para enlazar con otras fuentes de datos de películas están contenidos en el archivo. Cada línea de este archivo después de la fila de cabecera representa una película, y tiene el siguiente formato:links.csv

movieId,imdbId,tmdbId
movieId es un identificador para las películas que utilizan https://movielens.org. Por ejemplo, la película Toy Story tiene el enlace https://movielens.org/movies/1.

imdbId es un identificador para las películas que utilizan http://www.imdb.com. Por ejemplo, la película Toy Story tiene el enlace http://www.imdb.com/title/tt0114709/.

tmdbId es un identificador para las películas utilizadas por https://www.themoviedb.org. Por ejemplo, la película Toy Story tiene el enlace https://www.themoviedb.org/movie/862.

El uso de los recursos mencionados anteriormente está sujeto a los términos de cada proveedor.

Etiqueta Genoma (genome-scores.csv y genome-tags.csv)
Este conjunto de datos incluye una copia actual del Genoma de la Etiqueta.

El genoma de la etiqueta es una estructura de datos que contiene puntuaciones de relevancia de etiquetas para películas. La estructura es una matriz densa: cada película en el genoma tiene un valor para cada etiqueta en el genoma.

Como se describe en este artículo, el genoma de la etiqueta codifica la intensidad con la que las películas muestran propiedades particulares representadas por etiquetas (atmosférica, que invita a la reflexión, realista, etc.). El genoma de la etiqueta se calculó utilizando un algoritmo de aprendizaje automático sobre contenido aportado por usuarios, incluyendo etiquetas, valoraciones y revisiones textuales.

El genoma se divide en dos archivos. El archivo contiene datos de relevancia de etiquetas de películas en el siguiente formato:genome-scores.csv

movieId,tagId,relevance
El segundo archivo, , proporciona las descripciones de etiquetas para los identificadores de etiquetas en el archivo genómico, en el siguiente formato:genome-tags.csv

tagId,tag
Los valores se generan al exportar el conjunto de datos, por lo que pueden variar de una versión a otra de los conjuntos de datos de MovieLens.tagId

Por favor, incluye la siguiente cita si haces referencia a datos del genoma de la etiqueta:

Jesse Vig, Shilad Sen y John Riedl. 2012. El genoma de la etiqueta: codificando el conocimiento comunitario para apoyar la interacción novedosa. ACM Trans. Interactúa. Intel. Sisto 2, 3: 13:1–13:44. https://doi.org/10.1145/2362394.2362395

Validación cruzada
Las versiones anteriores del conjunto de datos MovieLens incluían bien pliegues cruzados precomputados o scripts para realizar este cálculo. Ya no agrupamos ninguna de estas características con el conjunto de datos, ya que la mayoría de los toolkits modernos la incluyen como función integrada. Si deseas aprender sobre enfoques estándar para la computación cross-fold en el contexto de la evaluación de sistemas recomendadores, consulta LensKit para herramientas, documentación y ejemplos de código abierto.