import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# --- SETUP INICIAL ---
load_dotenv()

# Configurar path para imports compartidos
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared_code.logger_config import setup_logger

# Inicializar Logger
logger = setup_logger('CAC_Scraper_Invernada')

# Constantes y Configuración
URL_API_PROXY = "https://www.decampoacampo.com/MODULOS/proxyPrecios/index.php"
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Diccionario de Meses
MESES = {
    "Ene": "01", "Feb": "02", "Mar": "03", "Abr": "04", "May": "05", "Jun": "06",
    "Jul": "07", "Ago": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dic": "12"
}

# Lista de Categorías Completa
CATEGORIAS_INVERNADA = [
    "Terneros -160 Kg.", "Terneros 160-180 Kg.", "Terneros 180-200 Kg.",
    "Terneros 200-230 Kg.", "Terneros 230-260 Kg.", "Novillitos 260-300 Kg.",
    "Novillitos +300 Kg.", "Ternero Holando", "Terneras -150 Kg.",
    "Terneras 150-170 Kg.", "Terneras 170-190 Kg.", "Terneras 190-210 Kg.",
    "Vaquillonas 210-250 Kg.", "Vaquillonas 250-290 Kg.", "Vaquillonas +290 Kg.",
    "Ternera Holando", "Vaquillonas Para Entorar", "Vaquillonas Preñadas",
    "Vacas de Invernada", "Vacas Nuevas Preñadas", "Vacas 1/2 diente Preñadas",
    "Vacas CUT Preñadas", "Vacas Nuevas con cría", "Vacas 1/2 diente con cría",
    "Vacas CUT con cría"
]

def get_robust_session():
    """Crea sesión HTTP resiliente para API JSON."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.decampoacampo.com/__dcac/invernada/invernada-precios'
    })
    return session

def determinar_tipo_hacienda(categoria):
    """Clasifica la categoría."""
    cat_lower = categoria.lower()
    if 'terneros' in cat_lower or 'novill' in cat_lower: return 'INVERNADA_MACHOS'
    elif 'terneras' in cat_lower: return 'INVERNADA_HEMBRAS'
    elif 'vaquillonas' in cat_lower:
        return 'INVERNADA_HEMBRAS' if 'kg' in cat_lower else 'INVERNADA_VIENTRES'
    elif 'vaca' in cat_lower: return 'INVERNADA_VIENTRES'
    return 'INVERNADA'

def limpiar_numero_campo(valor):
    """Limpia números del JSON."""
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.replace('.', '').replace(',', '.'))
        except ValueError:
            try: return float(valor.replace('.', ''))
            except ValueError: return 0.0
    return 0.0

def parsear_fecha_mensual(fecha_txt):
    """Convierte 'Ene 22' a '01/01/2022'."""
    try:
        partes = fecha_txt.split(' ')
        if len(partes) != 2: return None
        mes_num = MESES.get(partes[0].title())
        if not mes_num: return None
        return f"01/{mes_num}/20{partes[1]}"
    except Exception:
        return None

def completar_fecha_semanal(fecha_parcial):
    """Convierte '11/11' a '11/11/2025' con inteligencia de cambio de año."""
    if not fecha_parcial: return datetime.now().strftime("%d/%m/%Y")
    try:
        if len(fecha_parcial) > 5: return fecha_parcial
        dia, mes = map(int, fecha_parcial.split('/'))
        anio_actual = datetime.now().year
        if mes > datetime.now().month + 6: anio = anio_actual - 1
        else: anio = anio_actual
        return f"{dia:02d}/{mes:02d}/{anio}"
    except Exception:
        return datetime.now().strftime("%d/%m/%Y")

def scrape_invernada_diario(debug=False):
    """Scraper Semanal (Datos recientes)."""
    logger.info("Iniciando scraping diario de Invernada...")
    datos_totales = []
    
    URLS = [
        ('INVERNADA_MACHOS', 'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=1&m=peso'),
        ('INVERNADA_HEMBRAS', 'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=2&m=peso'),
        ('INVERNADA_VIENTRES', 'https://www.decampoacampo.com/gh_funciones.php?function=getListadoPreciosInvernada&p=3&m=peso')
    ]
    
    session = get_robust_session()
    
    for tipo, url in URLS:
        try:
            if debug: logger.debug(f"Consultando {tipo}...")
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            data_json = response.json()
            semana = data_json.get('semana_actual', {})
            f_ini = completar_fecha_semanal(semana.get('desde'))
            f_fin = completar_fecha_semanal(semana.get('hasta'))
            
            items = data_json.get('data', [])
            for item in items:
                reg = {
                    'fuente': 'DeCampoACampo',
                    'fecha_consulta_inicio': f_ini,
                    'fecha_consulta_fin': f_fin,
                    'tipo_hacienda': tipo,
                    'categoria_original': item.get('categoria'),
                    'raza': None,
                    'rango_peso': None,
                    'precio_promedio_kg': limpiar_numero_campo(item.get('precio_semana_1')),
                    'cabezas': int(item.get('cantidad_semana_1') or 0),
                    'variacion_semanal_precio': limpiar_numero_campo(item.get('variacion_precio_semana_1'))
                }
                if reg['categoria_original'] and reg['precio_promedio_kg']:
                    datos_totales.append(reg)

            time.sleep(1)

        except Exception as e:
            logger.error(f"Error obteniendo {tipo}: {e}")
            
    session.close()
    logger.info(f"Finalizado diario. {len(datos_totales)} registros obtenidos.")
    return datos_totales

def scrape_invernada_historico(debug=False):
    """Scraper Histórico (Mensual, 3 años)."""
    logger.info("Iniciando scraping histórico de Invernada (3 años)...")
    datos_totales = []
    
    session = get_robust_session()
    
    # Handshake inicial para setear cookies
    try: session.get('https://www.decampoacampo.com', timeout=10)
    except: pass

    for idx, cat in enumerate(CATEGORIAS_INVERNADA):
        if debug and idx % 5 == 0: logger.info(f"Procesando categoría {idx+1}/{len(CATEGORIAS_INVERNADA)}...")
        
        params = {
            'function': 'getTendenciaPreciosInvernadaTotalMonthly',
            'p': cat,
            'm': 'peso',
            'f': '3 years',
            '_': int(time.time() * 1000)
        }
        
        try:
            response = session.get(URL_API_PROXY, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # Parsear array de fechas stringficado
                fechas = json.loads(data.get('categorias', '[]'))
                series = data.get('series', [])
                
                if series and fechas:
                    precios = series[0].get('data', [])
                    if len(fechas) == len(precios):
                        for i, f_txt in enumerate(fechas):
                            f_fmt = parsear_fecha_mensual(f_txt)
                            precio = precios[i].get('y')
                            
                            if f_fmt and precio:
                                datos_totales.append({
                                    'fecha_consulta_inicio': f_fmt,
                                    'fecha_consulta_fin': f_fmt,
                                    'tipo_hacienda': determinar_tipo_hacienda(cat),
                                    'categoria_original': cat,
                                    'precio_promedio_kg': float(precio),
                                    'cabezas': 0,
                                    'variacion_semanal_precio': 0.0
                                })
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error procesando {cat}: {e}")

    session.close()
    logger.info(f"Finalizado histórico. {len(datos_totales)} registros obtenidos.")
    return datos_totales

if __name__ == "__main__":
    # Test
    d = scrape_invernada_diario(debug=True)
    if d: print(f"Ejemplo Diario: {d[0]}")