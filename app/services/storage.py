# services/storage.py

"""
Menyediakan kelas abstraksi untuk operasi penyimpanan file.

Modul ini berisi kelas JsonStorage yang menangani semua interaksi
baca dan tulis ke file JSON. Ini menyederhanakan pengelolaan data
knowledge base (rules, symptoms, diseases) dan memisahkan
logika I/O dari logika bisnis inti aplikasi.
"""

import json
import os
from typing import Any, Dict, List, Optional

class JsonStorage:
    """Kelas untuk membaca dan menulis data ke file JSON."""

    def read(self, file_path: str) -> Optional[Any]:
        """
        Membaca dan mem-parsing data dari sebuah file JSON.

        Args:
            file_path (str): Path ke file JSON.

        Returns:
            Optional[Any]: Data yang di-parsing (bisa list atau dict),
                           atau None jika file tidak ditemukan atau terjadi error.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            print(f"Error: File tidak ditemukan di '{file_path}'")
            return None
        except json.JSONDecodeError:
            print(f"Error: Gagal mem-parsing JSON dari '{file_path}'")
            return None
        except Exception as e:
            print(f"Terjadi error saat membaca file '{file_path}': {e}")
            return None

    def write(self, file_path: str, data: Any) -> bool:
        """
        Menulis data ke sebuah file JSON.

        Jika direktori tidak ada, akan dibuat secara otomatis.

        Args:
            file_path (str): Path tujuan file JSON.
            data (Any): Data yang akan ditulis (harus JSON-serializable).

        Returns:
            bool: True jika berhasil, False jika gagal.
        """
        try:
            # Pastikan direktori tujuan ada
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # indent=4 membuat file JSON lebih mudah dibaca manusia
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except TypeError as e:
            print(f"Error: Data tidak dapat diserialisasi ke JSON. Error: {e}")
            return False
        except Exception as e:
            print(f"Terjadi error saat menulis ke file '{file_path}': {e}")
            return False

# Contoh penggunaan di modul database_manager.py:
#
# from services.storage import JsonStorage
#
# storage = JsonStorage()
# rules_data = storage.read('database/rules.json')
# if rules_data:
#     # proses data
#     pass
#
# new_rule = {'id': 'R99', 'IF': ['G01'], 'THEN': 'P01', 'CF': 0.9}
# rules_data.append(new_rule)
# storage.write('database/rules.json', rules_data)