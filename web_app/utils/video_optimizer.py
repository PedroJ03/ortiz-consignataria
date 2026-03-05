import os
from moviepy import VideoFileClip

def optimizar_video(input_path, output_path):
    """
    Toma un video, lo redimensiona a 480p de alto, baja los FPS a 24
    y lo comprime para web.
    """
    try:
        # Cargar el video
        clip = VideoFileClip(input_path)
        
        # Opcional: Recortar si dura más de 60 segundos (Política de negocio)
        if clip.duration > 60:
            clip = clip.subclip(0, 60)

        # Redimensionar (Manteniendo relación de aspecto)
        # Height 480 es un estándar bueno para móviles (SD)
        if clip.h > 480:
            clip = clip.resize(height=480)
        
        # Escribir el archivo optimizado
        # preset='ultrafast' es vital para que el usuario no espere tanto
        # bitrate='500k' asegura que el peso sea muy bajo
        clip.write_videofile(
            output_path, 
            fps=24, 
            codec='libx264', 
            audio_codec='aac',
            preset='ultrafast',
            bitrate='800k',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None # Para no llenar la consola de logs
        )
        
        # Cerrar para liberar memoria (CRÍTICO en servidores compartidos)
        clip.close()
        return True

    except Exception as e:
        print(f"Error optimizando video: {e}")
        return False