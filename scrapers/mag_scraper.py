import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def limpiar_numero(texto_numero):
    """
    Función de ayuda para convertir un string de número (ej: "$1.234,56") a float.
    Devuelve 0.0 si la conversión falla.
    """
    if not texto_numero or not isinstance(texto_numero, str):
        return 0.0
    try:
        # Quita el símbolo '$', los espacios, los puntos y reemplaza la coma
        texto_limpio = texto_numero.strip().replace('$', '').replace('.', '')
        return float(texto_limpio.replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

def scrape_mag(fecha_inicio_str, fecha_fin_str, tipo_hacienda='TODOS', debug=False):
    """
    Scrapea la tabla del MAG usando una lógica de parseo flexible para
    manejar filas con diferente número de celdas.
    
    :param fecha_inicio_str: Fecha de inicio en formato "DD/MM/YYYY".
    :param fecha_fin_str: Fecha de fin en formato "DD/MM/YYYY".
    :param tipo_hacienda: 'TODOS', 'FAENA', o 'INVERNADA'.
    :param debug: Si es True, imprime información detallada del proceso.
    """
    
    URL = "https://www.mercadoagroganadero.com.ar/dll/hacienda6.dll/haciinfo000225"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Referer': URL
    }

    print(f"Iniciando scraper para MAG (Fechas: {fecha_inicio_str}-{fecha_fin_str}, Tipo: {tipo_hacienda})...")
    datos_mag = []

    try:
        with requests.Session() as s:
            s.headers.update(HEADERS)
            s.get(URL, timeout=20)

            mapa_tipo = {'TODOS': '0', 'FAENA': '1', 'INVERNADA': '2'}
            payload = {
                'txtFechaIni': fecha_inicio_str, 'txtFechaFin': fecha_fin_str,
                'LisTipo': mapa_tipo.get(tipo_hacienda, '0'), 'Submit': 'BUSCAR'
            }
            
            response_post = s.post(URL, data=payload, timeout=20)

            if response_post.status_code == 200:
                response_post.encoding = 'windows-1252'
                soup = BeautifulSoup(response_post.text, 'html.parser')
                
                tabla_datos = None
                for table in soup.find_all('table'):
                    if table.find(string=re.compile(r'Categoría')):
                        tabla_datos = table
                        if debug: print("DEBUG: ¡Tabla de datos encontrada por el encabezado 'Categoría'!")
                        break
                
                if tabla_datos:
                    filas = tabla_datos.find_all('tr')
                    if debug: print(f"DEBUG: ¡Éxito! Se encontraron {len(filas)} filas en total.")

                    for fila in filas:
                        celdas_texto = [td.get_text(strip=True) for td in fila.find_all('td')]
                        
                        # --- CORRECCIÓN CRÍTICA Y FLEXIBLE ---
                        # Aceptamos filas con 11 o 12 celdas.
                        # Nos aseguramos de que la segunda celda tenga contenido y no sea el pie de página.
                        if len(celdas_texto) >= 11 and celdas_texto[1] and 'Totales' not in celdas_texto[1]:
                            if debug: print(f"DEBUG: Procesando fila válida: {celdas_texto[1]}")
                            
                            # Rellenamos con '' si faltan celdas, para evitar errores de índice
                            while len(celdas_texto) < 12:
                                celdas_texto.append('')
                                
                            registro = {
                                'fuente': 'MAG_Analitico',
                                'fecha_consulta_inicio': fecha_inicio_str,
                                'fecha_consulta_fin': fecha_fin_str,
                                'tipo_hacienda': tipo_hacienda,
                                'categoria_original': celdas_texto[1],
                                'raza': celdas_texto[2],
                                'rango_peso': celdas_texto[3],
                                'precio_max_kg': limpiar_numero(celdas_texto[4]),
                                'precio_min_kg': limpiar_numero(celdas_texto[5]),
                                'precio_promedio_kg': limpiar_numero(celdas_texto[6]),
                                'precio_promedio_cabeza': limpiar_numero(celdas_texto[7]),
                                'cabezas': int(limpiar_numero(celdas_texto[8])),
                                'kilos_total': int(limpiar_numero(celdas_texto[9])),
                                'kilos_promedio_cabeza': int(limpiar_numero(celdas_texto[10])),
                                'importe_total': limpiar_numero(celdas_texto[11])
                            }
                            datos_mag.append(registro)
                else:
                    print("ADVERTENCIA: No se encontró la tabla de resumen en el HTML final.")
                    with open("debug_output.html", "w", encoding="utf-8") as f: f.write(response_post.text)
                    print(">>> Se ha guardado la respuesta HTML en 'debug_output.html' para análisis.")
            else:
                print(f"Error en la petición POST. Código de estado: {response_post.status_code}")

    except requests.RequestException as e:
        print(f"Error de conexión al scrapear MAG: {e}")

    print(f"Scraper MAG finalizado. Se encontraron {len(datos_mag)} registros.")
    return datos_mag


# --- Bloque para probar este script individualmente ---
if __name__ == "__main__":
    # Cambiamos los parámetros para una nueva prueba
    fecha_prueba = "9/10/2025"  # Un jueves
    tipo_prueba = "FAENA"
    
    print(f"--- Probando scraper para fecha: {fecha_prueba} y tipo: {tipo_prueba} ---")
    
    datos = scrape_mag(fecha_prueba, fecha_prueba, tipo_hacienda=tipo_prueba, debug=False)
    
    if datos:
        print(f"\n--- Registros Extraídos de MAG ({fecha_prueba} - {tipo_prueba}) ---")
        # Imprimimos todos los registros encontrados para esta prueba
        for fila in datos:
            print(fila)
    else:
        print("\nNo se encontraron datos para la selección.")

