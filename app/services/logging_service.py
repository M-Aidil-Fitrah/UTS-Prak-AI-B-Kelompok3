# services/logging_service.py

"""
Menyediakan layanan logging terpusat untuk aplikasi.

Modul ini mengkonfigurasi logger standar menggunakan library logging
bawaan Python. Ini memungkinkan semua bagian dari aplikasi untuk mencatat
informasi, peringatan, atau error ke dalam satu file log yang terstruktur.
Penggunaan RotatingFileHandler memastikan file log tidak membengkak
tanpa batas.
"""

import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "consultation_history.log")

def setup_logger(
    name: str = 'ExpertSystemLogger',
    log_file: str = LOG_FILE,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Mengkonfigurasi dan mengembalikan instance logger.

    Mencegah penambahan handler duplikat jika fungsi ini dipanggil
    beberapa kali.

    Args:
        name (str): Nama logger.
        log_file (str): Path ke file log.
        level (int): Level logging (misalnya, logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: Instance logger yang sudah dikonfigurasi.
    """
    # Pastikan direktori log ada
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    
    # Cek untuk menghindari penambahan handler berulang kali
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)

    # Buat formatter untuk mendefinisikan format log
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Buat handler untuk menulis log ke file, dengan rotasi
    # 5MB per file, dengan backup 5 file lama.
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    # Tambahkan handler ke logger
    logger.addHandler(handler)

    return logger

# Contoh penggunaan di modul lain:
# from services.logging_service import setup_logger
#
# logger = setup_logger()
# logger.info("Sesi konsultasi baru dimulai oleh user X.")
# logger.info("Gejala yang dipilih: ['G01', 'G05']")
# logger.info("Hasil diagnosis: Penyakit P02 dengan CF 0.85.")
# logger.error("Gagal memuat file rules.json.")