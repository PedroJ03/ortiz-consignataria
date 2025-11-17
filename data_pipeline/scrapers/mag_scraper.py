import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time # Para añadir pausa

# Requerido por el bloque de prueba si se ejecuta solo
from dotenv import load_dotenv
load_dotenv() 

def limpiar_numero(texto_numero):
    """
    Función de ayuda para convertir un string de número (ej: "$1.234,56") a float.
    Devuelve 0.0 si la conversión falla.
    """
    if not texto_numero or not isinstance(texto_numero, str):
        return 0.0
    try:
        texto_limpio = texto_numero.strip().replace('$', '')
        return float(texto_limpio.replace('.', '').replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

# --- Modificado: Ya no necesita tipo_hacienda como parámetro ---
def scrape_mag_faena(fecha_inicio_str, fecha_fin_str, debug=False):
    """
    Scrapea la tabla de FAENA del MAG para las fechas especificadas,
    obteniendo primero una sesión válida.
    
    :param fecha_inicio_str: Fecha de inicio en formato "DD/MM/YYYY".
    :param fecha_fin_str: Fecha de fin en formato "DD/MM/YYYY".
    :param debug: Si es True, imprime información detallada del proceso.
    :return: Lista de diccionarios con los datos de FAENA.
    """
    
    URL = "https://www.mercadoagroganadero.com.ar/dll/hacienda6.dll/haciinfo000225"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Referer': URL
    }
    
    # --- Modificado: Siempre buscará FAENA ---
    tipo_hacienda_fijo = 'FAENA' 
    print(f"Iniciando scraper para MAG (Fechas: {fecha_inicio_str}-{fecha_fin_str}, Tipo: {tipo_hacienda_fijo})...")
    datos_mag = []

    try:
        with requests.Session() as s:
            s.headers.update(HEADERS)
            if debug: print("DEBUG: Paso 1 - Obteniendo cookie de sesión...")
            # Visita inicial para obtener cookies
            response_get = s.get(URL, timeout=20)
            if response_get.status_code != 200:
                 print(f"Error al obtener página inicial. Código: {response_get.status_code}")
                 return []
            if debug: print("DEBUG: Cookie de sesión obtenida.")

            # --- Modificado: Payload siempre para FAENA (LisTipo='1') ---
            payload = {
                'txtFechaIni': fecha_inicio_str, 
                'txtFechaFin': fecha_fin_str,
                'LisTipo': '1', # Código para FAENA
                'Submit': 'BUSCAR' 
            }
            
            if debug: print(f"DEBUG: Paso 2 - Enviando POST con payload: {payload}")
            response_post = s.post(URL, data=payload, timeout=20)

            if response_post.status_code == 200:
                response_post.encoding = 'windows-1252'
                soup = BeautifulSoup(response_post.text, 'html.parser')
                
                tabla_datos = None
                # Buscar tabla por contenido ("Categoría")
                for table in soup.find_all('table'):
                    header_row = table.find('tr')
                    if header_row and header_row.find(string=re.compile(r'Categor.a')): # Usamos regex flexible
                        tabla_datos = table
                        if debug: print("DEBUG: ¡Tabla de datos encontrada por encabezado!")
                        break
                
                if tabla_datos:
                    filas = tabla_datos.find_all('tr')
                    if debug: print(f"DEBUG: Se encontraron {len(filas)} filas en total.")

                    for fila_idx, fila in enumerate(filas):
                         # Evitar filas de encabezado (podrían ser varias en esta tabla)
                        if fila.find('th') or fila_idx < 2: # Si tiene <th> o es de las primeras 2, probablemente es header
                            if debug: print(f"DEBUG: Fila {fila_idx+1} ignorada (posible encabezado).")
                            continue
                            
                        celdas_texto = [td.get_text(strip=True) for td in fila.find_all('td')]
                        
                        # Ajustar condición al número real de columnas de datos (excluyendo vacía inicial)
                        if len(celdas_texto) >= 11 and celdas_texto[1] and 'Totales' not in celdas_texto[1]: 
                            if debug: print(f"DEBUG: Procesando fila válida: {celdas_texto[1]}")
                            
                            while len(celdas_texto) < 12: celdas_texto.append('') # Asegurar 12 elementos
                                
                            registro = {
                                'fuente': 'MAG_Faena', # <-- Modificado
                                'fecha_consulta_inicio': fecha_inicio_str,
                                'fecha_consulta_fin': fecha_fin_str,
                                'tipo_hacienda': tipo_hacienda_fijo, # <-- Modificado
                                'categoria_original': celdas_texto[1], 'raza': celdas_texto[2], 
                                'rango_peso': celdas_texto[3],
                                'precio_max_kg': limpiar_numero(celdas_texto[4]), 
                                'precio_min_kg': limpiar_numero(celdas_texto[5]),
                                'precio_promedio_kg': limpiar_numero(celdas_texto[6]),
                                # 'precio_promedio_cabeza': limpiar_numero(celdas_texto[7]), # Eliminado según BBDD
                                'cabezas': int(limpiar_numero(celdas_texto[8])),
                                'kilos_total': int(limpiar_numero(celdas_texto[9])),
                                # 'kilos_promedio_cabeza': int(limpiar_numero(celdas_texto[10])), # Eliminado según BBDD
                                'importe_total': limpiar_numero(celdas_texto[11])
                            }
                            datos_mag.append(registro)
                        elif debug and celdas_texto and celdas_texto[1]: # No imprimir warnings para filas vacías
                             print(f"DEBUG: Fila ignorada (no cumple criterios): {celdas_texto}")
                else:
                    print("ADVERTENCIA: No se encontró la tabla de resumen en el HTML final.")
                    # Guardar HTML para depuración si falla la búsqueda de tabla
                    # with open("debug_output_mag_faena.html", "w", encoding="utf-8") as f: f.write(response_post.text)
                    # print(">>> Se ha guardado la respuesta HTML en 'debug_output_mag_faena.html'.")
            else:
                print(f"Error en la petición POST. Código de estado: {response_post.status_code}")

    except requests.RequestException as e:
        print(f"Error de conexión al scrapear MAG Faena: {e}")
    except Exception as e:
        print(f"Error inesperado al procesar MAG Faena: {e}")
        import traceback
        traceback.print_exc()

    print(f"Scraper MAG ({tipo_hacienda_fijo}) finalizado. Se encontraron {len(datos_mag)} registros.")
    return datos_mag

# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    fecha_prueba = "17/10/2025" # Viernes
    print(f"--- Probando scraper MAG (Solo Faena) para fecha: {fecha_prueba} ---")
    
    # Llamamos a la función específica (ahora solo hay una)
    datos = scrape_mag_faena(fecha_prueba, fecha_prueba, debug=True) 
    
    if datos:
        print(f"\n--- Primeros 5 Registros Extraídos de MAG (Faena - {fecha_prueba}) ---")
        for fila in datos[:5]:
            print("-" * 20)
            for key, value in fila.items():
                 print(f"  {key}: {value}")
    else:
        print("\nNo se encontraron datos.")

