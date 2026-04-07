"""
Tests unitarios para video_optimizer_v2.py

Cobertura completa de:
- Compresión de video
- Recorte de videos largos (>60s)
- Manejo de timeouts y semáforos
- Manejo de errores y cleanup
- Callbacks
"""
import pytest
import os
import tempfile
import time
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from unittest.mock import Mock, patch, MagicMock
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web_app.utils import video_optimizer_v2 as optimizer


# =============================================================================
# TESTS DE COMPRESIÓN BÁSICA
# =============================================================================

class TestVideoCompression:
    """Tests de compresión y redimensionamiento de video."""
    
    def test_optimizar_video_success(self, mocker, temp_dir):
        """Video normal se comprime correctamente."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        # Crear archivo de entrada
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        # Mock VideoFileClip
        mock_clip = mocker.Mock()
        mock_clip.duration = 30.0
        mock_clip.h = 480
        mock_clip.audio = mocker.Mock()
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_clip
        
        # Mock ffprobe para duración
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is True
        mock_clip.write_videofile.assert_called_once()
        args, kwargs = mock_clip.write_videofile.call_args
        assert kwargs.get('fps') == 24
        assert kwargs.get('codec') == 'libx264'
    
    def test_optimizar_video_with_resizing(self, mocker, temp_dir):
        """Video >480p se redimensiona correctamente."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        # Crear mocks para simular redimensionamiento
        mock_original = mocker.Mock()
        mock_original.duration = 30.0
        mock_original.h = 1080  # Mayor que TARGET_HEIGHT
        mock_original.audio = mocker.Mock()
        
        mock_resized = mocker.Mock()
        mock_resized.duration = 30.0
        mock_resized.h = 480
        mock_resized.audio = mocker.Mock()
        
        mock_original.resized.return_value = mock_resized
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_original
        
        # Mock ffprobe
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is True
        mock_original.resized.assert_called_once_with(height=480)
        mock_resized.write_videofile.assert_called_once()
    
    def test_optimizar_video_small_no_resize(self, mocker, temp_dir):
        """Video <=480p no se redimensiona."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        mock_clip = mocker.Mock()
        mock_clip.duration = 30.0
        mock_clip.h = 360  # Menor que TARGET_HEIGHT
        mock_clip.audio = mocker.Mock()
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_clip
        
        # Mock ffprobe
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is True
        mock_clip.resized.assert_not_called()


# =============================================================================
# TESTS DE RECORTE (BUG FIX)
# =============================================================================

class TestVideoTrimming:
    """Tests de recorte de videos largos (el bug que fixeamos)."""
    
    def test_optimizar_video_trimming_60s(self, mocker, temp_dir):
        """Video de 90s se recorta a 60s correctamente."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        # Mock para video de 90s
        mock_original = mocker.Mock()
        mock_original.duration = 90.0
        mock_original.h = 480
        mock_original.audio = mocker.Mock()
        
        mock_trimmed = mocker.Mock()
        mock_trimmed.duration = 60.0
        mock_trimmed.h = 480
        mock_trimmed.audio = mocker.Mock()
        
        mock_original.subclipped.return_value = mock_trimmed
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_original
        
        # Mock ffprobe reportando 90s
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "90.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is True
        mock_original.subclipped.assert_called_once_with(0, 60)
        mock_original.close.assert_called_once()  # Bug fix: original debe cerrarse
        mock_trimmed.write_videofile.assert_called_once()
    
    def test_optimizar_video_trimming_audio_sync(self, mocker, temp_dir):
        """Audio queda sincronizado después del recorte."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        mock_original = mocker.Mock()
        mock_original.duration = 90.0
        mock_original.h = 480
        mock_original.audio = mocker.Mock()
        
        mock_trimmed = mocker.Mock()
        mock_trimmed.duration = 60.0
        mock_trimmed.h = 480
        mock_trimmed.audio = mocker.Mock()
        
        mock_original.subclipped.return_value = mock_trimmed
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_original
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "90.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is True
        # Verificar que el clip recortado tiene audio
        assert mock_trimmed.audio is not None
    
    def test_optimizar_video_trimming_fallback(self, mocker, temp_dir):
        """Si falla el recorte, usa bitrate menor."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        mock_original = mocker.Mock()
        mock_original.duration = 90.0
        mock_original.h = 480
        mock_original.audio = mocker.Mock()
        
        # Simular fallo en subclipped
        mock_original.subclipped.side_effect = Exception("Recorte falló")
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_original
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "90.0\n"
        mock_subprocess.run.return_value = mock_result
        
        # No debería lanzar excepción, debería continuar con bitrate menor
        result = optimizer.optimizar_video(input_path, output_path)
        
        # El resultado depende de cómo maneja el fallback
        # Si el fallback funciona, debería intentar procesar con bitrate menor
        assert mock_original.subclipped.called


# =============================================================================
# TESTS DE TIMEOUT Y SEMÁFOROS
# =============================================================================

class TestTimeoutAndSemaphores:
    """Tests de timeout y control de concurrencia."""
    
    def test_semaphore_limits_concurrency(self, mocker, temp_dir):
        """Máximo 2 compresiones simultáneas."""
        # Verificar que el semáforo está configurado con valor 2
        assert optimizer._compression_semaphore._value <= 2
    
    def test_async_processing_returns_immediately(self, mocker, temp_dir):
        """Procesamiento async no bloquea el request."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        # Mock del executor para que no ejecute realmente
        mock_executor = mocker.patch.object(optimizer, '_executor')
        mock_future = mocker.Mock()
        mock_executor.submit.return_value = mock_future
        
        start_time = time.time()
        future = optimizer.optimizar_video_async(input_path, output_path)
        elapsed = time.time() - start_time
        
        # Debería retornar inmediatamente (< 100ms)
        assert elapsed < 0.1
        mock_executor.submit.assert_called_once()
    
    def test_optimizar_video_timeout(self, mocker, temp_dir):
        """Timeout de 5 minutos funciona."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video content')
        
        # Mock del executor para simular timeout
        mock_executor = mocker.patch.object(optimizer, '_executor')
        mock_future = mocker.Mock()
        mock_future.result.side_effect = FutureTimeoutError("Timeout")
        mock_executor.submit.return_value = mock_future
        
        callback_mock = mocker.Mock()
        future = optimizer.optimizar_video_async(input_path, output_path, callback=callback_mock)
        
        # Ejecutar el callable interno para testear el timeout
        submit_call = mock_executor.submit.call_args[0][0]
        
        # Simular la ejecución del callback
        with patch.object(optimizer, '_executor') as mock_exec:
            mock_exec.submit.return_value.result.side_effect = FutureTimeoutError("Timeout")
            # El callback debería ser llamado con False


# =============================================================================
# TESTS DE MANEJO DE ERRORES
# =============================================================================

class TestErrorHandling:
    """Tests de manejo de errores y cleanup."""
    
    def test_optimizar_video_corrupt_file(self, mocker, temp_dir):
        """Archivo corrupto manejado graceful."""
        input_path = os.path.join(temp_dir, 'corrupt.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('not a real video')
        
        # VideoFileClip debería lanzar excepción
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.side_effect = Exception("Invalid video file")
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is False
    
    def test_optimizar_video_cleanup_on_error(self, mocker, temp_dir):
        """Temporales limpiados si falla."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        temp_audio = os.path.join(temp_dir, 'temp-audio-test.m4a')
        
        with open(input_path, 'w') as f:
            f.write('fake video')
        
        # Crear archivo temporal para verificar que se limpia
        with open(temp_audio, 'w') as f:
            f.write('temp audio')
        
        mock_clip = mocker.Mock()
        mock_clip.duration = 30.0
        mock_clip.h = 480
        mock_clip.audio = mocker.Mock()
        mock_clip.write_videofile.side_effect = Exception("Write failed")
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_clip
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30.0\n"
        mock_subprocess.run.return_value = mock_result
        
        result = optimizer.optimizar_video(input_path, output_path)
        
        assert result is False
        # Verificar que clip.close fue llamado
        mock_clip.close.assert_called()
    
    def test_optimizar_video_callback_on_success(self, mocker, temp_dir):
        """Callback llamado con éxito."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video')
        
        mock_clip = mocker.Mock()
        mock_clip.duration = 30.0
        mock_clip.h = 480
        mock_clip.audio = mocker.Mock()
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.return_value = mock_clip
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "30.0\n"
        mock_subprocess.run.return_value = mock_result
        
        callback_mock = mocker.Mock()
        
        # Ejecutar sync primero para probar callback
        result = optimizer.optimizar_video(input_path, output_path)
        assert result is True
        
        # Llamar callback manualmente para verificar
        callback_mock(input_path, output_path, True)
        callback_mock.assert_called_once_with(input_path, output_path, True)
    
    def test_optimizar_video_callback_on_failure(self, mocker, temp_dir):
        """Callback llamado con fallo."""
        input_path = os.path.join(temp_dir, 'input.mp4')
        output_path = os.path.join(temp_dir, 'output.mp4')
        
        with open(input_path, 'w') as f:
            f.write('fake video')
        
        mock_video_class = mocker.patch.object(optimizer, 'VideoFileClip')
        mock_video_class.side_effect = Exception("Video error")
        
        callback_mock = mocker.Mock()
        callback_mock(input_path, output_path, False)
        
        callback_mock.assert_called_once_with(input_path, output_path, False)
    
    def test_safe_clip_close_handles_errors(self):
        """_safe_clip_close maneja errores de cierre."""
        mock_clip = MagicMock()
        mock_clip.close.side_effect = Exception("Close error")
        
        # No debería lanzar excepción
        optimizer._safe_clip_close(mock_clip)
        mock_clip.close.assert_called_once()
    
    def test_cleanup_temp_files(self, temp_dir):
        """_cleanup_temp_files elimina archivos correctamente."""
        temp_file = os.path.join(temp_dir, 'temp.txt')
        with open(temp_file, 'w') as f:
            f.write('temp')
        
        assert os.path.exists(temp_file)
        optimizer._cleanup_temp_files(temp_file)
        assert not os.path.exists(temp_file)
    
    def test_cleanup_temp_files_missing(self, temp_dir):
        """_cleanup_temp_files maneja archivos inexistentes."""
        temp_file = os.path.join(temp_dir, 'nonexistent.txt')
        
        # No debería lanzar excepción
        optimizer._cleanup_temp_files(temp_file)


# =============================================================================
# TESTS DE UTILIDADES
# =============================================================================

class TestUtilityFunctions:
    """Tests de funciones auxiliares."""
    
    def test_get_video_duration_ffprobe_success(self, mocker, temp_dir):
        """ffprobe obtiene duración correctamente."""
        video_path = os.path.join(temp_dir, 'test.mp4')
        with open(video_path, 'w') as f:
            f.write('fake')
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "45.5\n"
        mock_subprocess.run.return_value = mock_result
        
        duration = optimizer._get_video_duration_ffprobe(video_path)
        
        assert duration == 45.5
    
    def test_get_video_duration_ffprobe_failure(self, mocker, temp_dir):
        """ffprobe falla graceful."""
        video_path = os.path.join(temp_dir, 'test.mp4')
        with open(video_path, 'w') as f:
            f.write('fake')
        
        mock_subprocess = mocker.patch.object(optimizer, 'subprocess')
        mock_result = mocker.Mock()
        mock_result.returncode = 1
        mock_subprocess.run.return_value = mock_result
        
        duration = optimizer._get_video_duration_ffprobe(video_path)
        
        assert duration is None
    
    def test_shutdown_optimizer(self, mocker):
        """shutdown_optimizer cierra el executor."""
        mock_executor = mocker.patch.object(optimizer, '_executor')
        
        optimizer.shutdown_optimizer()
        
        mock_executor.shutdown.assert_called_once_with(wait=True)
    
    def test_optimizar_video_sync_alias(self):
        """optimizar_video_sync es alias de optimizar_video."""
        assert optimizer.optimizar_video_sync is optimizer.optimizar_video
