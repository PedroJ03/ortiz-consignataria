import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import sys
import os
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---
# 1. Cargar variables de entorno
load_dotenv()

# 2. Configurar path para importar shared_code (Monorepo)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared_code.logger_config import setup_logger

# 3. Inicializar Logger
logger = setup_logger('MAG_Scraper')

# 4. Constantes desde .env
URL_BASE_GET = os.getenv('MAG_URL_BASE')
URL_ACTION_POST = os.getenv('MAG_URL_POST')
MAG_USER = os.getenv('MAG_USER')
MAG_CP = os.getenv('MAG_CP')
USER_AGENT = os.getenv('USER_AGENT')

def get_robust_session():
    """
    Genera una sesión HTTP con estrategia de reintentos (Exponential Backoff).
    Esencial para evitar fallos por micro-cortes de red.
    """
    session = requests.Session()
    # Reintentar 3 veces en errores 500, 502, 503, 504
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.9',
        'Origin': 'https://www.mercadoagroganadero.com.ar',
        'Referer': URL_BASE_GET
    })
    return session

def inicializar_sesion_mag(session):
    """
    ESTRATEGIA JERÁRQUICA (ORDEN PROFESIONAL):
    1. Intentar obtener credencial FRESCA (Cookies/Headers) -> Evita bloqueos y expiración.
    2. Intentar obtener credencial del HTML -> Método estándar.
    3. Usar Credencial MAESTRA (Hardcoded) -> Solo si el servidor falla al darnos una nueva.
    """
    try:
        logger.info("Iniciando handshake...")
        
        # Petición GET para simular entrada de usuario real
        response = session.get(URL_BASE_GET, timeout=15)
        response.raise_for_status()
        
        # ESTRATEGIA 1: COOKIES (La más robusta para este tipo de webs viejas)
        # Si el servidor nos dio una cookie "ID", la usamos. Es la credencial más "limpia".
        id_sesion = session.cookies.get('ID')
        
        if id_sesion:
            logger.info(f"Estrategia 1 (Cookies) exitosa. ID: {id_sesion[:8]}...")
            
        # ESTRATEGIA 2: HTML (Backup dinámico)
        # Si no hay cookie, miramos si vino en el HTML (aunque vimos que a veces viene vacío)
        if not id_sesion:
            soup = BeautifulSoup(response.text, 'html.parser')
            input_id = soup.find('input', {'name': 'ID'})
            if input_id and input_id.get('value'):
                id_sesion = input_id.get('value')
                logger.info(f"Estrategia 2 (HTML) exitosa. ID: {id_sesion[:8]}...")

        # ESTRATEGIA 3: FALLBACK ESTATICO (Tu ID Maestro)
        # Si el servidor no nos dio nada (o envió campos vacíos), usamos el comodín.
        if not id_sesion:
            logger.warning("El servidor no entregó ID dinámico. Activando ID Maestro de respaldo.")
            id_sesion = "E0E7EC0C-8211-496C-A67F-DAFBF0E6983E" # Tu ID conocido

        # Construimos los inputs para el formulario
        hidden_inputs = {
            'ID': id_sesion,
            'CP': MAG_CP,
            'USUARIO': MAG_USER,
            'OPCIONMENU': '',
            'OPCIONSUBMENU': ''
        }
        
        return hidden_inputs

    except Exception as e:
        # Si falla la conexión del handshake, incluso ahí podemos intentar usar el ID maestro
        # directamente contra el POST, aunque es arriesgado, es un último recurso válido.
        logger.error(f"Fallo en conexión handshake: {e}. Intentando forzar ID Maestro.")
        return {
            'ID': "E0E7EC0C-8211-496C-A67F-DAFBF0E6983E",
            'CP': MAG_CP,
            'USUARIO': MAG_USER
        }

def limpiar_numero(texto_numero):
    """Parsea números con formato argentino (1.234,56) a float."""
    if not texto_numero or not isinstance(texto_numero, str):
        return 0.0
    try:
        clean = texto_numero.strip().replace('$', '').replace(' ', '')
        if not clean or clean == '-': return 0.0
        return float(clean.replace('.', '').replace(',', '.'))
    except Exception:
        return 0.0

def parsear_categoria_string(texto_completo):
    """
    Separa la cadena de categoría en sus componentes lógicos.
    Ej: "NOVILLOS Esp.Joven + 430" -> ("NOVILLOS", "Esp.Joven", "+ 430")
    """
    texto_completo = texto_completo.strip()
    
    # Patrón 1: Con peso explicito (h o +)
    patron_peso = re.match(r'^(\w+)\s+(.+?)\s+([h\+])\s+(\d+)$', texto_completo)
    if patron_peso:
        # Grupo 1: Cat, 2: Raza, 3: Operador, 4: Valor
        return patron_peso.group(1), patron_peso.group(2), f"{patron_peso.group(3)} {patron_peso.group(4)}"
    
    # Patrón 2: Sin peso (solo calidad)
    patron_simple = re.match(r'^(\w+)\s+(.+)$', texto_completo)
    if patron_simple:
        return patron_simple.group(1), patron_simple.group(2), ""
    
    # Fallback
    return texto_completo, "", ""

def validar_estructura_tabla(table_soup):
    """Verifica que la tabla tenga las columnas esperadas (Defensa ante cambios del sitio)."""
    headers = [th.get_text(strip=True).lower() for th in table_soup.find_all('th')]
    headers_txt = " ".join(headers)
    # Palabras clave críticas que deben existir
    required = ['categoría', 'mínimo', 'máximo', 'promedio', 'cabezas', 'importe', 'kgs']
    
    missing = [w for w in required if w not in headers_txt]
    if missing:
        logger.critical(f"ESTRUCTURA DE TABLA ALTERADA. Faltan: {missing}")
        return False
    return True

def scrape_mag_faena(fecha_inicio_str, fecha_fin_str, debug=False):
    """Función principal de scraping."""
    session = get_robust_session()
    datos_procesados = []

    try:
        # 1. Obtener parámetros dinámicos
        params_sesion = inicializar_sesion_mag(session)
        if not params_sesion:
            return []

        # 2. Construir Payload
        payload = params_sesion.copy()
        payload.update({
            'txtFechaIni': fecha_inicio_str,
            'txtFechaFin': fecha_fin_str,
            'CP': MAG_CP,
            'USUARIO': MAG_USER,
            'OPCIONMENU': '', # A veces el servidor lo requiere vacío
        })

        # 3. Ejecutar POST
        logger.info(f"Consultando datos para: {fecha_inicio_str}")
        response = session.post(URL_ACTION_POST, data=payload, timeout=30)
        response.encoding = 'windows-1252' # Forzar encoding correcto

        if response.status_code != 200:
            logger.error(f"Error HTTP {response.status_code} en POST.")
            return []

        # 4. Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar tabla por contenido
        target_table = None
        for table in soup.find_all('table'):
            txt = table.get_text().lower()
            if 'mediana' in txt and 'precios' in txt:
                target_table = table
                break
        
        if not target_table:
            logger.warning(f"No se encontraron datos para la fecha {fecha_inicio_str}.")
            return []

        if not validar_estructura_tabla(target_table):
            return []

        # 5. Extraer Datos
        rows = target_table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols_text = [c.get_text(strip=True) for c in cols]
            
            # Validar fila de datos
            if len(cols_text) < 9: continue

            raw_cat = cols_text[0]
            # 1. Si la categoría está vacía
            if not raw_cat: 
                continue
            
            # 2. Si es una fila de separación o totales
            if "-------" in raw_cat or "Total" in raw_cat or "Prom." in raw_cat:
                continue

            try:
                cat, raza, peso = parsear_categoria_string(cols_text[0])
                cabezas = int(limpiar_numero(cols_text[5]))
                
                if cabezas == 0: continue

                registro = {
                    'fecha_consulta_inicio': fecha_inicio_str,
                    'tipo_hacienda': 'FAENA',
                    'categoria_original': cat,
                    'raza': raza,
                    'rango_peso': peso,
                    'precio_min_kg': limpiar_numero(cols_text[1]),
                    'precio_max_kg': limpiar_numero(cols_text[2]),
                    'precio_promedio_kg': limpiar_numero(cols_text[3]),
                    'cabezas': cabezas,
                    'importe_total': limpiar_numero(cols_text[6]),
                    'kilos_total': int(limpiar_numero(cols_text[7])),
                    # Nota: col 8 son kgs promedio/cabeza, col 7 total
                }
                datos_procesados.append(registro)

            except Exception as e:
                logger.warning(f"Error al parsear fila: {cols_text[0]} - {e}")
                continue

    except Exception as e:
        logger.exception("Error no controlado durante el scraping.")
        return []
    finally:
        session.close()

    logger.info(f"Finalizado. {len(datos_procesados)} registros obtenidos.")
    return datos_procesados

# Bloque de prueba rápida
if __name__ == "__main__":
    # Fecha de prueba (asegurate de que sea un día hábil reciente)
    test_date = "19/11/2025"
    print(f"Probando scraper profesional para {test_date}...")
    data = scrape_mag_faena(test_date, test_date, debug=True)
    if data:
        print(f"Éxito. Primer registro: {data[0]}")
    else:
        print("No se obtuvieron datos.")