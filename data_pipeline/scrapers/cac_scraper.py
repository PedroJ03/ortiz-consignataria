import requests
import json
import time
from datetime import datetime
import urllib.parse

# --- Configuración ---
URL_API = "https://www.decampoacampo.com/MODULOS/proxyPrecios/index.php"

# Lista de categorías COMPLETA (Machos, Hembras, Vientres)
CATEGORIAS_INVERNADA = [
    # --- MACHOS ---
    "Terneros -160 Kg.",
    "Terneros 160-180 Kg.",
    "Terneros 180-200 Kg.",
    "Terneros 200-230 Kg.",
    "Terneros 230-260 Kg.",
    "Novillitos 260-300 Kg.",
    "Novillitos +300 Kg.",
    "Ternero Holando",
    
    # --- HEMBRAS ---
    "Terneras -150 Kg.",
    "Terneras 150-170 Kg.",
    "Terneras 170-190 Kg.",
    "Terneras 190-210 Kg.",
    "Vaquillonas 210-250 Kg.",
    "Vaquillonas 250-290 Kg.",
    "Vaquillonas +290 Kg.",
    "Ternera Holando",
    
    # --- VIENTRES / VACAS ---
    "Vaquillonas Para Entorar",
    "Vaquillonas Preñadas",
    "Vacas de Invernada",
    "Vacas Nuevas Preñadas",
    "Vacas 1/2 diente Preñadas",
    "Vacas CUT Preñadas",
    "Vacas Nuevas con cría",
    "Vacas 1/2 diente con cría",
    "Vacas CUT con cría"
]

# Diccionario para parsear fechas del histórico
MESES = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04", "May": "05", "Jun": "06",
    "Jul": "07", "Ago": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12"
}

def get_headers():
    """Devuelve headers para simular un navegador real."""
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.decampoacampo.com/__dcac/invernada/invernada-precios',
        'Connection': 'keep-alive'
    }

def determinar_tipo_hacienda(categoria):
    """Clasifica la categoría en Machos, Hembras o Vientres."""
    cat_lower = categoria.lower()
    
    if 'terneros' in cat_lower or 'novill' in cat_lower:
        return 'INVERNADA_MACHOS'
    elif 'terneras' in cat_lower:
        return 'INVERNADA_HEMBRAS'
    elif 'vaquillonas' in cat_lower:
        # Si tiene 'kg', es por peso (Hembra para engorde).
        # Si no (ej. 'preñadas'), es Vientre.
        if 'kg' in cat_lower:
            return 'INVERNADA_HEMBRAS'
        else:
            return 'INVERNADA_VIENTRES'
    elif 'vaca' in cat_lower:
        return 'INVERNADA_VIENTRES'
    
    return 'INVERNADA' # Default

def limpiar_numero_campo(valor):
    """Limpia números del JSON de CampoACampo (pueden ser int, float o string)."""
    if isinstance(valor, (int, float)):
        return float(valor)
    elif isinstance(valor, str):
        try:
            # Quitar puntos de miles y usar coma como decimal
            return float(valor.replace('.', '').replace(',', '.'))
        except ValueError:
            # Intentar quitar solo puntos si la coma no era decimal
            try:
                return float(valor.replace('.', ''))
            except ValueError:
                 return 0.0 # O None, según prefieras manejar errores
    return 0.0 # O None

def parsear_fecha_mensual(fecha_txt):
    """Convierte 'Ene 22' a '01/01/2022'."""
    try:
        partes = fecha_txt.split(' ')
        if len(partes) != 2: return None
        
        mes_txt = partes[0].title()
        anio_corto = partes[1]
        
        mes_num = MESES.get(mes_txt)
        if not mes_num: return None
        
        return f"01/{mes_num}/20{anio_corto}"
    except Exception:
        return None

def completar_fecha_semanal(fecha_parcial):
    """
    Convierte '11/11' a '11/11/2025'.
    Maneja el cambio de año (si estamos en enero y la fecha es de diciembre).
    """
    if not fecha_parcial:
        return datetime.now().strftime("%d/%m/%Y")
        
    try:
        # Si ya tiene año (len > 5), devolver tal cual
        if len(fecha_parcial) > 5:
            return fecha_parcial
            
        dia, mes = map(int, fecha_parcial.split('/'))
        anio_actual = datetime.now().year
        
        # Lógica simple: si el mes es mayor al mes actual + 6, probablemente es del año pasado
        # (Ej: estamos en Enero 2025 y llega '28/12')
        mes_actual = datetime.now().month
        if mes > mes_actual + 6:
            anio = anio_actual - 1
        else:
            anio = anio_actual
            
        return f"{dia:02d}/{mes:02d}/{anio}"
    except Exception:
        return datetime.now().strftime("%d/%m/%Y") # Fallback

def scrape_invernada_diario(debug=False):
    """
    Obtiene los datos de Invernada (Machos, Hembras, Vientres) desde los
    endpoints JSON de DeCampoACampo y los combina.
    Extrae los datos de la semana actual.
    """
    print("Iniciando scraper para DeCampoACampo (Invernada)...")
    datos_invernada_total = []
    
    URLS_JSON_CAMPO = [
        'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=1&m=peso', # Machos
        'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=2&m=peso', # Hembras
        'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=3&m=peso'  # Vientres
    ]
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Referer': 'https://www.decampoacampo.com/', # Simular venir de la página principal
        'Accept': 'application/json, text/javascript, */*; q=0.01', # Indicar que esperamos JSON
        'X-Requested-With': 'XMLHttpRequest' # Indicar que es una petición AJAX
    }

    for url in URLS_JSON_CAMPO:
        tipo_hacienda_actual = "INVERNADA" # Tipo general
        if 'p=1' in url: tipo_hacienda_actual = "INVERNADA_MACHOS"
        elif 'p=2' in url: tipo_hacienda_actual = "INVERNADA_HEMBRAS"
        elif 'p=3' in url: tipo_hacienda_actual = "INVERNADA_VIENTRES"
        
        print(f"--- Obteniendo datos para: {tipo_hacienda_actual} ---")
        if debug: print(f"DEBUG: URL: {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status() # Lanza error si status no es 200
            
            data_json = response.json()
            
            if debug:
                 print(f"DEBUG: JSON recibido para {tipo_hacienda_actual} (primeros 500 chars):")
                 print(json.dumps(data_json, indent=2, ensure_ascii=False)[:500] + "\n...") 

            semana_info = data_json.get('semana_actual', {})
            
            raw_desde = semana_info.get('desde') # ej "11/11"
            raw_hasta = semana_info.get('hasta') # ej "18/11"
            
            # CORRECCIÓN: Agregar el año
            fecha_inicio = completar_fecha_semanal(raw_desde)
            fecha_fin = completar_fecha_semanal(raw_hasta)

            lista_data = data_json.get('data', [])

            for item in lista_data:
                categoria = item.get('categoria')
                # Usaremos los datos de 'semana_1' consistentemente
                cantidad = item.get('cantidad_semana_1') 
                # El precio parece ser promedio, aunque el JSON no lo especifica
                precio_promedio = item.get('precio_semana_1') 
                variacion = item.get('variacion_precio_semana_1') 
                
                if categoria and precio_promedio is not None: 
                     registro = {
                         'fuente': 'DeCampoACampo',
                         'fecha_consulta_inicio': fecha_inicio, 
                         'fecha_consulta_fin': fecha_fin,
                         'tipo_hacienda': tipo_hacienda_actual, # Usamos el tipo específico
                         'categoria_original': categoria,
                         'raza': None, 
                         'rango_peso': None, # Podríamos intentar parsearlo de la categoría luego
                         'precio_promedio_kg': limpiar_numero_campo(precio_promedio),
                         'cabezas': int(cantidad) if cantidad is not None else 0,
                         'variacion_semanal_precio': limpiar_numero_campo(variacion),
                         # --- Campos Nulos ---
                         'precio_max_kg': None,
                         'precio_min_kg': None,
                         'kilos_total': None, 
                         'importe_total': None 
                     }
                     datos_invernada_total.append(registro)
                     if debug:
                         print(f"DEBUG: Procesado: {categoria} ({tipo_hacienda_actual}) - Precio: {registro['precio_promedio_kg']}")
                elif debug:
                     print(f"DEBUG: Item JSON ignorado por falta de datos: {item}")
            
            # Práctica Profesional: Pequeña pausa para no sobrecargar el servidor
            time.sleep(1) 

        except requests.exceptions.Timeout:
             print(f"ERROR: Timeout al intentar obtener datos de {url}")
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión al obtener JSON de {url}: {e}")
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON de {url}: {e}")
            if 'response' in locals(): print("Respuesta:", response.text[:500])
        except Exception as e:
            print(f"Error inesperado procesando {url}: {e}")
            import traceback
            traceback.print_exc()

    print(f"Scraper DeCampoACampo (Invernada) finalizado. Se encontraron {len(datos_invernada_total)} registros en total.")
    return datos_invernada_total

# --- FUNCIÓN 2: SCRAPER HISTÓRICO (Para backfill) ---
def scrape_invernada_historico(debug=False):
    """
    Obtiene 3 AÑOS de historia mensual usando el endpoint 'TotalMonthly'.
    Devuelve una lista de diccionarios lista para la BBDD.
    """
    print(f"--- Iniciando Scraper Invernada (Modo Histórico) ---")
    datos_totales = []
    
    with requests.Session() as s:
        s.headers.update(get_headers())
        try: s.get('https://www.decampoacampo.com/__dcac/invernada/invernada-precios', timeout=10)
        except: pass 

        for categoria in CATEGORIAS_INVERNADA:
            if debug: print(f"Consultando histórico: {categoria}...")
            
            # Endpoint Mensual
            params = {
                'function': 'getTendenciaPreciosInvernadaTotalMonthly',
                'p': categoria,
                'm': 'peso',
                'f': '3 years',
                '_': int(time.time() * 1000)
            }

            try:
                response = s.get(URL_API, params=params, timeout=15)
                if response.status_code == 200:
                    data_json = response.json()
                    
                    # 1. Parsear las fechas (String JSON dentro del JSON)
                    categorias_str = data_json.get('categorias', '[]')
                    try:
                        fechas_raw = json.loads(categorias_str) # ["Ene 22", "Feb 22", ...]
                    except json.JSONDecodeError:
                        if debug: print(f"Error decodificando fechas para {categoria}")
                        continue

                    # 2. Obtener los precios
                    series = data_json.get('series', [])
                    
                    if series and fechas_raw:
                        precios_data = series[0].get('data', [])
                        
                        # Validar que longitudes coincidan
                        if len(fechas_raw) == len(precios_data):
                            count_cat = 0
                            for i, fecha_txt in enumerate(fechas_raw):
                                precio_info = precios_data[i]
                                precio = precio_info.get('y')
                                
                                # Convertir fecha
                                fecha_fmt = parsear_fecha_mensual(fecha_txt)
                                
                                if precio and fecha_fmt:
                                    registro = {
                                        'fecha_consulta_inicio': fecha_fmt, 
                                        'fecha_consulta_fin': fecha_fmt,
                                        'tipo_hacienda': determinar_tipo_hacienda(categoria),
                                        'categoria_original': categoria,
                                        'precio_promedio_kg': float(precio),
                                        'cabezas': 0, 
                                        'variacion_semanal_precio': 0.0
                                    }
                                    datos_totales.append(registro)
                                    count_cat += 1
                            
                            if debug: print(f"  -> Recuperados {count_cat} registros históricos.")
                        else:
                            if debug: print(f"Desajuste de longitud: fechas={len(fechas_raw)}, datos={len(precios_data)}")
            except Exception as e:
                print(f"Error procesando {categoria}: {e}")
            
            time.sleep(1) 

    print(f"Scraper Histórico finalizado. Registros obtenidos: {len(datos_totales)}")
    return datos_totales

# Bloque de prueba
if __name__ == "__main__":
    print("--- Probando Modo Diario (Solo 1 categoría) ---")
    # Hacemos un override temporal para prueba rápida
    CATS_ORIGINAL = CATEGORIAS_INVERNADA
    CATEGORIAS_INVERNADA = [CATEGORIAS_INVERNADA[0]] 
    
    datos_diarios = scrape_invernada_diario(debug=True)
    if datos_diarios: print(f"Dato diario: {datos_diarios[-1]}")

    print("\n--- Probando Modo Histórico (Solo 1 categoría) ---")
    datos_hist = scrape_invernada_historico(debug=True)
    if datos_hist: print(f"Dato histórico: {datos_hist[-1]}")
    
    # Restaurar lista
    CATEGORIAS_INVERNADA = CATS_ORIGINAL

