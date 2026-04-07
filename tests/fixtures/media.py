"""
Fixtures de archivos multimedia para tests.
"""
import pytest
import os
import tempfile
import io


@pytest.fixture
def sample_jpg_content():
    """Contenido mínimo válido de una imagen JPEG."""
    # JPEG mínimo válido (header JFIF)
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9
    ])


@pytest.fixture
def sample_png_content():
    """Contenido mínimo válido de una imagen PNG."""
    # PNG signature + IHDR chunk mínimo
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D,  # IHDR length
        0x49, 0x48, 0x44, 0x52,  # IHDR
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02, 0x00, 0x00, 0x00,  # IHDR data
        0x90, 0x77, 0x53, 0xDE,  # IHDR CRC
        0x00, 0x00, 0x00, 0x00,  # IEND length
        0x49, 0x45, 0x4E, 0x44,  # IEND
        0xAE, 0x42, 0x60, 0x82   # IEND CRC
    ])


@pytest.fixture
def sample_mp4_content():
    """Contenido mínimo que parece un MP4 (no es un video real, pero tiene magic bytes de ftqt)."""
    # ftyp box para MP4
    return bytes([
        0x00, 0x00, 0x00, 0x18,  # size
        0x66, 0x74, 0x79, 0x70,  # 'ftyp'
        0x69, 0x73, 0x6F, 0x6D,  # major_brand 'isom'
        0x00, 0x00, 0x00, 0x00,  # minor_version
        0x69, 0x73, 0x6F, 0x6D,  # compatible_brands[0]
        0x6D, 0x70, 0x34, 0x31   # compatible_brands[1]
    ])


@pytest.fixture
def sample_gif_content():
    """Contenido mínimo válido de un GIF."""
    return b'GIF89a' + bytes(100)


@pytest.fixture
def fake_jpg_as_exe():
    """Archivo que finge ser JPG pero es realmente ejecutable."""
    # Header de JPG seguido de contenido de ejecutable
    exe_content = b'\x4D\x5A' + b'MZ' + b'PE' + b'\x00\x00'  # Windows executable header
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0
    ]) + exe_content


@pytest.fixture
def image_file_factory(temp_dir):
    """Factory para crear archivos de imagen de prueba."""
    def factory(filename='test_image.jpg', content=None, size=1024):
        filepath = os.path.join(temp_dir, filename)
        
        if content is None:
            # Crear un JPEG mínimo válido
            content = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00
            ]) + b'\xFF\xD9'  # Padding + EOI marker
            # Rellenar al tamaño deseado
            content = content + b'\x00' * (size - len(content))
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return filepath
    return factory


@pytest.fixture
def video_file_factory(temp_dir):
    """Factory para crear archivos de video de prueba."""
    def factory(filename='test_video.mp4', content=None, size=10240):
        filepath = os.path.join(temp_dir, filename)
        
        if content is None:
            # Crear un MP4 mínimo (ftyp box)
            content = bytes([
                0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70,
                0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x00, 0x00,
                0x69, 0x73, 0x6F, 0x6D, 0x6D, 0x70, 0x34, 0x31
            ])
            # Rellenar al tamaño deseado
            content = content + b'\x00' * (size - len(content))
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return filepath
    return factory


@pytest.fixture
def large_file_factory(temp_dir):
    """Factory para crear archivos grandes."""
    def factory(filename='large_file.bin', size_mb=101):
        filepath = os.path.join(temp_dir, filename)
        size_bytes = size_mb * 1024 * 1024
        
        with open(filepath, 'wb') as f:
            # Escribir en chunks de 1MB para no usar mucha memoria
            chunk = b'\x00' * (1024 * 1024)
            for _ in range(size_mb):
                f.write(chunk)
        
        return filepath
    return factory
