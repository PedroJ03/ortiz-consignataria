import requests
import json
from datetime import datetime
import time # Para añadir un pequeño retardo entre peticiones

# URLs encontradas para los datos de Invernada (Machos, Hembras, Vientres)
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

def scrape_invernada_campo(debug=False):
    """
    Obtiene los datos de Invernada (Machos, Hembras, Vientres) desde los
    endpoints JSON de DeCampoACampo y los combina.
    Extrae los datos de la semana actual.
    """
    print("Iniciando scraper para DeCampoACampo (Invernada)...")
    datos_invernada_total = []
    
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

            semana_actual_info = data_json.get('semana_actual', {})
            fecha_inicio_semana = semana_actual_info.get('desde', datetime.now().strftime('%d/%m/%Y')) # Fallback a hoy
            fecha_fin_semana = semana_actual_info.get('hasta', datetime.now().strftime('%d/%m/%Y')) # Fallback a hoy
            
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
                         'fecha_consulta_inicio': fecha_inicio_semana, 
                         'fecha_consulta_fin': fecha_fin_semana,
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

# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    datos = scrape_invernada_campo(debug=True)
    
    if datos:
        print("\n--- Primeros 5 Registros Extraídos de DeCampoACampo (Invernada) ---")
        for fila in datos[:5]:
            print("-" * 20)
            for key, value in fila.items():
                 print(f"  {key}: {value}")
    else:
        print("\nNo se pudieron extraer datos.")

