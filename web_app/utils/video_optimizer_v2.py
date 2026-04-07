"""
Video Optimizer V2 - Optimización de video con procesamiento asíncrono
y fix del bug de recorte en videos > 60 segundos.

Mejoras:
- Fix del bug de recorte (cierra clip correctamente, maneja excepciones)
- Optimizaciones de rendimiento (threads, preset, crf)
- Procesamiento asíncrono con ThreadPoolExecutor
- Semáforo para limitar compresiones simultáneas
- Timeout de 5 minutos por video
- Callback para notificar resultado
- Limpieza garantizada de temporales
- Logging detallado
"""

import os
import subprocess
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import partial
from typing import Callable, Optional

from moviepy import VideoFileClip

# Configurar logging detallado
logger = logging.getLogger(__name__)

# Semáforo para limitar compresiones simultáneas (máximo 2)
_compression_semaphore = threading.Semaphore(2)

# Executor global para procesamiento asíncrono
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="video_opt_")

# Constantes de configuración
MAX_DURATION_SECONDS = 60
TARGET_HEIGHT = 480
TARGET_FPS = 24
VIDEO_CODEC = 'libx264'
AUDIO_CODEC = 'aac'
TIMEOUT_SECONDS = 300  # 5 minutos


def _get_video_duration_ffprobe(video_path: str) -> Optional[float]:
    """
    Obtiene la duración real del video usando ffprobe.
    Fallback confiable cuando MoviePy no reporta correctamente.
    
    Args:
        video_path: Ruta al archivo de video
        
    Returns:
        Duración en segundos o None si falla
    """
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe falló para {video_path}: {e}")
    return None


def _safe_clip_close(clip):
    """Cierra un clip de forma segura, ignorando errores."""
    if clip is not None:
        try:
            clip.close()
        except Exception as e:
            logger.debug(f"Error cerrando clip (ignorado): {e}")


def _cleanup_temp_files(*files):
    """Limpia archivos temporales de forma segura."""
    for filepath in files:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Temporal eliminado: {filepath}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar temporal {filepath}: {e}")


def optimizar_video(input_path: str, output_path: str) -> bool:
    """
    Versión síncrona: Toma un video, lo recorta a 60s si es necesario,
    redimensiona a 480p, baja FPS a 24 y comprime para web.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta donde guardar el video optimizado
        
    Returns:
        True si tuvo éxito, False en caso contrario
    """
    temp_audio_file = None
    clip = None
    needs_cleanup = []
    
    try:
        logger.info(f"Iniciando optimización: {input_path}")
        
        # 1. Cargar el video
        logger.debug(f"Cargando video: {input_path}")
        clip = VideoFileClip(input_path)
        needs_cleanup.append(('clip', clip))
        
        # 2. Validar duración con ffprobe como fallback
        duration_moviepy = clip.duration
        duration_ffprobe = _get_video_duration_ffprobe(input_path)
        
        if duration_ffprobe is not None:
            logger.debug(f"Duración MoviePy: {duration_moviepy:.2f}s, ffprobe: {duration_ffprobe:.2f}s")
            # Usar la mayor duración detectada para no perder contenido
            actual_duration = max(duration_moviepy, duration_ffprobe)
        else:
            actual_duration = duration_moviepy
            logger.debug(f"Duración (MoviePy): {actual_duration:.2f}s")
        
        # 3. Recortar si dura más de 60 segundos
        if actual_duration > MAX_DURATION_SECONDS:
            logger.info(f"Video dura {actual_duration:.2f}s, recortando a {MAX_DURATION_SECONDS}s")
            try:
                # Cerrar el clip actual antes de recortar
                original_clip = clip
                
                # Crear nuevo clip recortado
                clip = clip.subclipped(0, MAX_DURATION_SECONDS)
                needs_cleanup.append(('clip_recortado', clip))
                
                # Cerrar el original después de crear el recorte
                _safe_clip_close(original_clip)
                needs_cleanup = [('clip_recortado', clip)]  # Actualizar lista
                
                logger.debug("Recorte exitoso")
                
            except Exception as e:
                logger.error(f"Error en recorte: {e}. Intentando procesar video completo con bitrate más bajo.")
                # Fallback: procesar completo pero con bitrate más bajo
                # No recortamos, continuamos con el clip original
                pass
        
        # 4. Redimensionar manteniendo relación de aspecto
        if clip.h > TARGET_HEIGHT:
            logger.debug(f"Redimensionando de {clip.h}p a {TARGET_HEIGHT}p")
            clip = clip.resized(height=TARGET_HEIGHT)
            needs_cleanup.append(('clip_resized', clip))
        
        # 5. Configurar archivo de audio temporal único
        temp_audio_file = f"temp-audio-{threading.current_thread().ident}-{int(time.time())}.m4a"
        
        # Determinar bitrate basado en si se recortó o no
        # Si no se pudo recortar (fallback), usar bitrate más bajo
        if actual_duration > MAX_DURATION_SECONDS and clip.duration > MAX_DURATION_SECONDS:
            bitrate = '500k'  # Más bajo para videos largos que no se pudieron recortar
            logger.info(f"Usando bitrate reducido ({bitrate}) para video largo sin recortar")
        else:
            bitrate = '800k'
        
        # 6. Escribir archivo optimizado con mejoras de rendimiento
        logger.info(f"Escribiendo video optimizado: {output_path}")
        clip.write_videofile(
            output_path,
            fps=TARGET_FPS,
            codec=VIDEO_CODEC,
            audio_codec=AUDIO_CODEC,
            preset='veryfast',  # Cambio: de 'ultrafast' a 'veryfast' (mejor compresión, casi misma velocidad)
            bitrate=bitrate,
            threads=4,  # NUEVO: Usar 4 threads para procesamiento más rápido
            ffmpeg_params=['-crf', '23'],  # NUEVO: Calidad constante rate factor
            temp_audiofile=temp_audio_file,
            remove_temp=True,
            verbose=False,  # NUEVO: Menos overhead de logging
            logger=None
        )
        
        logger.info(f"Optimización exitosa: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error optimizando video {input_path}: {e}", exc_info=True)
        
        # No guardar archivo sin optimizar si falla - peligroso
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.warning(f"Archivo de salida parcial eliminado: {output_path}")
            except Exception as cleanup_e:
                logger.error(f"No se pudo eliminar archivo parcial: {cleanup_e}")
        
        return False
        
    finally:
        # Limpieza garantizada de todos los recursos
        logger.debug("Iniciando limpieza de recursos")
        
        # Cerrar clips en orden inverso
        for name, resource in reversed(needs_cleanup):
            _safe_clip_close(resource)
        
        # Limpiar archivo de audio temporal si quedó
        _cleanup_temp_files(temp_audio_file)
        
        logger.debug("Limpieza completada")


def _optimizar_video_with_semaphore(input_path: str, output_path: str) -> bool:
    """
    Wrapper que adquiere el semáforo antes de procesar.
    Usado internamente por la versión async.
    """
    logger.debug(f"Esperando semáforo para procesar: {input_path}")
    with _compression_semaphore:
        logger.debug(f"Semáforo adquirido, procesando: {input_path}")
        return optimizar_video(input_path, output_path)


def optimizar_video_async(
    input_path: str,
    output_path: str,
    callback: Optional[Callable[[str, str, bool], None]] = None
) -> 'concurrent.futures.Future[bool]':
    """
    Versión asíncrona: Procesa el video en un thread separado con semáforo.
    
    Args:
        input_path: Ruta al video de entrada
        output_path: Ruta donde guardar el video optimizado
        callback: Función opcional callback(input_path, output_path, success)
        
    Returns:
        Future que se resuelve con True/False según el resultado
        
    Example:
        def mi_callback(input_path, output_path, success):
            if success:
                print(f"Video listo: {output_path}")
            else:
                print(f"Falló: {input_path}")
        
        future = optimizar_video_async("input.mp4", "output.mp4", callback=mi_callback)
        # El usuario recibe respuesta inmediata: "procesando..."
    """
    def _process_with_timeout_and_callback():
        """Función interna que ejecuta el procesamiento con timeout y callback."""
        try:
            # Ejecutar con timeout usando el semáforo
            future_sync = _executor.submit(_optimizar_video_with_semaphore, input_path, output_path)
            success = future_sync.result(timeout=TIMEOUT_SECONDS)
            
            logger.info(f"Procesamiento async completado: {input_path} -> {success}")
            
            # Llamar callback si se proporcionó
            if callback:
                try:
                    callback(input_path, output_path, success)
                except Exception as cb_e:
                    logger.error(f"Error en callback: {cb_e}")
            
            return success
            
        except FutureTimeoutError:
            logger.error(f"Timeout después de {TIMEOUT_SECONDS}s procesando: {input_path}")
            
            # Limpiar archivo parcial si existe
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            
            # Notificar fallo via callback
            if callback:
                try:
                    callback(input_path, output_path, False)
                except Exception:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error en procesamiento async: {e}", exc_info=True)
            
            if callback:
                try:
                    callback(input_path, output_path, False)
                except Exception:
                    pass
            
            return False
    
    # Enviar al executor
    future = _executor.submit(_process_with_timeout_and_callback)
    logger.debug(f"Tarea async enviada: {input_path}")
    
    return future


def shutdown_optimizer():
    """
    Cierra limpiamente el executor. Llamar al cerrar la aplicación.
    """
    logger.info("Cerrando Video Optimizer V2...")
    _executor.shutdown(wait=True)
    logger.info("Video Optimizer V2 cerrado")


# Alias para compatibilidad hacia atrás
optimizar_video_sync = optimizar_video


if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Prueba simple
    import sys
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        print(f"Procesando {input_file} -> {output_file}")
        result = optimizar_video(input_file, output_file)
        print(f"Resultado: {'ÉXITO' if result else 'FALLO'}")
    else:
        print("Uso: python video_optimizer_v2.py <input.mp4> <output.mp4>")
