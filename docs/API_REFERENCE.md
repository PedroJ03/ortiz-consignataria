# Referencia de la API Interna

El sistema expone varios endpoints REST internos utilizados principalmente por el Dashboard dinámico para poblar gráficos y filtros sin recargar la página. Todas las respuestas se entregan en formato `JSON`.

## Resumen de Endpoints

| Endpoint | Método | Descripción |
| :--- | :--- | :--- |
| `/api/faena` | `GET` | Obtiene el histórico de precios del Mercado Agroganadero (MAG) para Faena. |
| `/api/invernada` | `GET` | Obtiene el histórico de precios de Tendencias (CAC) para Invernada. |
| `/api/categorias` | `GET` | Obtiene la lista unificada de categorías excluyendo las listas negras. |
| `/api/subcategorias` | `GET` | Obtiene jerárquicamente las razas y pesos según una categoría padre. |

---

## Detalle de Endpoints

### 1. Histórico de Faena
`GET /api/faena`

Devuelve los registros históricos de precios base (MAG) filtrados por un rango de fechas obligatorio y filtros opcionales.

**Parámetros Query:**
* `start` (String, Requerido): Fecha de inicio en formato `YYYY-MM-DD`.
* `end` (String, Requerido): Fecha de fin en formato `YYYY-MM-DD`.
* `categoria` (String, Opcional): Filtra por categoría original (ej. "Novillitos").
* `raza` (String, Opcional): Filtra por raza.
* `rango_peso` (String, Opcional): Filtra por rango de kilaje.

**Respuestas:**
* `200 OK`: Devuelve un arreglo de objetos JSON (definido por el manager SQL).
* `400 Bad Request`: Si omiten las fechas (`{"error": "Fechas requeridas"}`).
* `500 Internal Server Error`: Falla interna de la base de datos.

---

### 2. Histórico de Invernada
`GET /api/invernada`

Devuelve la lista histórica de precios de la categoría Invernada.

**Parámetros Query:**
* `start` (String, Requerido): Fecha de inicio en formato `YYYY-MM-DD`.
* `end` (String, Requerido): Fecha de fin en formato `YYYY-MM-DD`.
* `categoria` (String, Opcional): Filtra por sub-categoría específica.

**Respuestas:**
* `200 OK`: Arreglo JSON de los registros.
* `400 Bad Request`: Si faltan los parámetros base.
* `500 Internal Server Error`: Falla interna.

---

### 3. Listado Unificado de Categorías
`GET /api/categorias`

Obtiene todas las categorías posibles separadas por el gran dominio (Faena vs Invernada). 
*Nota: Este endpoint excluye automáticamente las categorías configuradas en la constante interna `CATEGORIAS_EXCLUIDAS` (Ej: "Ternera Holando", "Vacas CUT con cría") y descarta cruzas.*

**Respuestas:**
* `200 OK`:
  ```json
  {
    "faena": ["Novillos", "Novillitos", "Vacas Buena"],
    "invernada": ["Terneros", "Vaquillonas"]
  }
  ```
* `500 Internal Server Error`: Falla de BBDD.

---

### 4. Búsqueda de Sub-Categorías (Cascada)
`GET /api/subcategorias`

Devuelve dinámicamente las razas asociadas y los rangos de peso atados a una categoría padre para rellenar campos combo select dependientes.

**Parámetros Query:**
* `categoria` (String, Requerido): La categoría madre seleccionada.
* `raza` (String, Opcional): Si se pasa, los rangos de peso devueltos se acotan solo a esa raza en específico.

**Respuestas:**
* `200 OK`:
  ```json
  {
    "razas": ["Angus", "Hereford"],
    "pesos": ["300-350 kg", "350-400 kg"]
  }
  ```
* `400 Bad Request`: Si no se provee la categoría obligatoria (`{"error": "Categoria requerida"}`).
* `500 Internal Server Error`: Falla interna de la BBDD.
