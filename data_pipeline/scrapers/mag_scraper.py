import requests
from bs4 import BeautifulSoup
import time

# URL del formulario de consultas históricas
URL_MAG_FORM = "https://www.mercadoagroganadero.com.ar/dll/hacienda6.dll/haciinfo000225"

def limpiar_numero(texto_numero):
    """Convierte string numérico argentino (1.234,56) a float."""
    if not texto_numero or not isinstance(texto_numero, str):
        return 0.0
    try:
        # Eliminar símbolos y espacios
        texto_limpio = texto_numero.strip().replace('$', '').replace(' ', '')
        # Formato argentino: punto para miles, coma para decimales
        return float(texto_limpio.replace('.', '').replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0

def scrape_mag_faena(fecha_inicio_str, fecha_fin_str, debug=False):
    """
    Scraper robusto para MAG (Faena) v2.1.
    Incluye captura de Importe Total.
    """
    print(f"--- Consultando MAG para rango: {fecha_inicio_str} - {fecha_fin_str} ---")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': URL_MAG_FORM,
        'Origin': 'https://www.mercadoagroganadero.com.ar',
        'Connection': 'keep-alive'
    }

    datos_procesados = []

    try:
        with requests.Session() as s:
            s.headers.update(headers)
            
            # --- PASO 1: GET para obtener tokens ---
            if debug: print("1. Obteniendo formulario inicial...")
            response_get = s.get(URL_MAG_FORM, timeout=15)
            response_get.encoding = response_get.apparent_encoding
            
            if response_get.status_code != 200:
                print(f"Error al acceder al formulario inicial: {response_get.status_code}")
                return []

            soup_get = BeautifulSoup(response_get.text, 'html.parser')
            
            payload = {
                'txtFechaIni': fecha_inicio_str,
                'txtFechaFin': fecha_fin_str,
                'LisTipo': '1', # 1 = Faena
                'OPCIONMENU': '',
                'OPCIONSUBMENU': ''
            }
            
            for hidden_name in ['ID', 'CP', 'USUARIO', 'FLASH']:
                input_tag = soup_get.find('input', {'name': hidden_name})
                if input_tag:
                    payload[hidden_name] = input_tag.get('value', '')
            
            # --- PASO 2: POST con la consulta ---
            if debug: print("2. Enviando consulta POST...")
            time.sleep(1) 

            response_post = s.post(URL_MAG_FORM, data=payload, timeout=30)
            response_post.encoding = response_post.apparent_encoding 

            if response_post.status_code != 200:
                print(f"Error HTTP {response_post.status_code} en la consulta POST.")
                return []

            # --- PASO 3: Parseo ---
            soup = BeautifulSoup(response_post.text, 'html.parser')

            target_table = None
            for table in soup.find_all('table'):
                headers_text = table.get_text().lower()
                if 'categor' in headers_text and 'prom' in headers_text:
                    target_table = table
                    break
            
            if not target_table:
                print("ADVERTENCIA: No se encontró la tabla de resultados.")
                return []

            rows = target_table.find_all('tr')
            
            for row in rows:
                cols = row.find_all('td')
                cols_text = [c.get_text(strip=True) for c in cols]
                
                # Estructura típica (puede variar, por eso usamos len):
                # 0: (Vacio)
                # 1: Categoría
                # 2: Raza
                # 3: Peso
                # 4: Max
                # 5: Min
                # 6: Promedio
                # 7: Mediana (a veces)
                # 8: Cabezas
                # 9: Kgs Total
                # 10: Cab. Prom (a veces)
                # 11: Importe Total (Última columna usualmente)
                
                if len(cols_text) < 9: continue
                
                categoria = cols_text[1]
                if not categoria or "Total" in categoria or "Categoría" in categoria:
                    continue

                try:
                    # Cabezas suele estar en la columna 8
                    cabezas_idx = 8
                    if not cols_text[cabezas_idx].replace('.','').isdigit():
                         # Si no es un número, intentar buscar la columna correcta
                         # (Heurística simple: buscar la primera columna entera > 0 desde la derecha)
                         pass 

                    cabezas = int(limpiar_numero(cols_text[cabezas_idx]))
                    if cabezas == 0: continue

                    precio_prom = limpiar_numero(cols_text[6])
                    
                    # Intentar capturar Importe Total (usualmente la última columna con datos)
                    # Probamos la col 11 (si existe), o la última
                    importe_total = 0.0
                    if len(cols_text) >= 12:
                        importe_total = limpiar_numero(cols_text[11])
                    elif len(cols_text) >= 10:
                         # A veces está antes
                         importe_total = limpiar_numero(cols_text[-1])

                    registro = {
                        'fecha_consulta_inicio': fecha_inicio_str,
                        'tipo_hacienda': 'FAENA',
                        'categoria_original': categoria,
                        'raza': cols_text[2] if cols_text[2] else '',
                        'rango_peso': cols_text[3] if cols_text[3] else '',
                        'precio_min_kg': limpiar_numero(cols_text[5]),
                        'precio_max_kg': limpiar_numero(cols_text[4]),
                        'precio_promedio_kg': precio_prom,
                        'cabezas': cabezas,
                        'kilos_total': int(limpiar_numero(cols_text[9])),
                        'importe_total': importe_total # <-- AHORA CAPTURADO
                    }
                    datos_procesados.append(registro)
                    
                except (ValueError, IndexError):
                    continue 

    except Exception as e:
        print(f"Error en scraper MAG: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return []

    return datos_procesados

# Prueba rápida
if __name__ == "__main__":
    # Usamos una fecha reciente hábil
    fecha_test = "14/11/2025" 
    print(f"Probando scraper para {fecha_test}...")
    datos = scrape_mag_faena(fecha_test, fecha_test, debug=True)
    
    print(f"\nResultados: {len(datos)} registros encontrados.")
    if datos:
        print("Primer registro completo:")
        print(datos[0])