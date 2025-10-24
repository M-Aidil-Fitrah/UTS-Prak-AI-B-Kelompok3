# services/storage.py

"""
Menyediakan kelas abstraksi untuk operasi penyimpanan file dan consultation history.

Modul ini berisi:
- JsonStorage: Kelas untuk baca/tulis file JSON umum
- StorageService: Kelas untuk mengelola consultation history dengan integrasi database

Memisahkan logika I/O dari logika bisnis inti aplikasi.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

# Import database functions untuk integrasi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database_manager import load_rules

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


class StorageService:
    """Service untuk mengelola consultation history dengan integrasi database.
    
    Menyediakan fungsi untuk:
    - Simpan hasil konsultasi/diagnosis
    - Load history konsultasi
    - Filter dan search history
    - Export history
    - Enrich data dengan detail dari database
    """
    
    def __init__(self, history_dir: str = "data/history"):
        """Initialize StorageService.
        
        Args:
            history_dir: Direktori untuk menyimpan history files
        """
        self.history_dir = history_dir
        self.history_file = os.path.join(history_dir, "consultations.json")
        self.json_storage = JsonStorage()
        
        # Pastikan direktori ada
        os.makedirs(history_dir, exist_ok=True)
        
        # Load database paths
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        self.symptoms_path = os.path.join(base_path, "symptoms.json")
        self.diseases_path = os.path.join(base_path, "diseases.json")
    
    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file helper."""
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_symptoms_by_ids(self, symptom_ids: List[str]) -> List[Dict[str, Any]]:
        """Ambil detail symptoms dari database."""
        symptoms_data = self._load_json(self.symptoms_path)
        found_symptoms = []

        if isinstance(symptoms_data, dict):
            for sid in symptom_ids:
                if sid in symptoms_data:
                    symptom_details = symptoms_data[sid].copy() # Use copy to avoid modifying original
                    symptom_details['id'] = sid
                    found_symptoms.append(symptom_details)
        elif isinstance(symptoms_data, list):
            # Create a lookup dictionary for faster access if it's a list
            symptoms_dict = {s['id']: s for s in symptoms_data if 'id' in s}
            for sid in symptom_ids:
                if sid in symptoms_dict:
                    found_symptoms.append(symptoms_dict[sid])
        
        return found_symptoms
    
    def _get_disease_by_id(self, disease_id: str) -> Optional[Dict[str, Any]]:
        """Ambil detail disease dari database."""
        diseases = self._load_json(self.diseases_path)
        # Cek apakah diseases adalah list atau dict untuk kompatibilitas
        if isinstance(diseases, dict):
            return diseases.get(disease_id)
        elif isinstance(diseases, list):
            # Jika ini adalah daftar, cari secara manual
            for disease in diseases:
                if disease.get("id") == disease_id:
                    return disease
        return None
    
    def save_consultation(
        self, 
        symptom_ids: List[str], 
        diagnosis_result: Dict[str, Any], 
        user_cf: float,
        user_info: Optional[Dict[str, Any]] = None
    ):
        """Menyimpan satu konsultasi ke file history utama."""
        # 1. Muat history yang ada
        history = self.json_storage.read(self.history_file)
        if history is None:
            history = [] # Buat list baru jika file tidak ada atau error

        # Pastikan history adalah list
        if not isinstance(history, list):
            print(f"Warning: File history '{self.history_file}' bukan list. Membuat file baru.")
            history = []

        # 2. Buat data untuk disimpan
        consultation_id = f"C_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
        
        data_to_save = {
            "consultation_id": consultation_id,
            "timestamp": datetime.now().isoformat(),
            "user_info": user_info or {},
            "user_cf": user_cf,
            "symptoms": {
                "ids": symptom_ids,
                "count": len(symptom_ids)
            },
            "diagnosis": diagnosis_result
        }
        
        # 3. Tambahkan konsultasi baru ke awal list (agar yang terbaru di atas)
        history.insert(0, data_to_save)
        
        # 4. Tulis kembali seluruh history ke file
        try:
            if self.json_storage.write(self.history_file, history):
                return consultation_id
            else:
                raise IOError("Gagal menulis ke file history.")
        except Exception as e:
            raise IOError(f"Gagal menyimpan file konsultasi: {e}")

    def load_consultation_history(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Load consultation history dari file.
        
        Args:
            limit: Batasi jumlah history yang dikembalikan (latest first)
            
        Returns:
            List consultation data, sorted by timestamp descending
        """
        # Load dari file
        history = self.json_storage.read(self.history_file)
        
        # Jika file belum ada atau kosong
        if not history:
            return []
        
        # Sort by timestamp descending (terbaru dulu)
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Limit jika diberikan
        if limit:
            history = history[:limit]
        
        return history
    
    def get_consultation_by_id(self, consultation_id: str) -> Optional[Dict[str, Any]]:
        """Ambil consultation detail berdasarkan ID.
        
        Args:
            consultation_id: ID consultation yang dicari
            
        Returns:
            Dictionary consultation data atau None jika tidak ditemukan
        """
        history = self.load_consultation_history()
        
        for consultation in history:
            if consultation.get('id') == consultation_id:
                return consultation
        
        return None
    
    def search_consultations(
        self,
        history: List[Dict[str, Any]],
        query: Optional[str] = None,
        disease_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search consultations dengan berbagai filter dari list history yang sudah di-load.
        
        Args:
            history: List of consultations to search within.
            query: Kata kunci untuk search di ID atau disease name
            disease_filter: Filter by disease ID
            date_from: Filter dari tanggal (YYYY-MM-DD)
            date_to: Filter sampai tanggal (YYYY-MM-DD)
            
        Returns:
            List filtered consultations
        """
        results = []
        
        for consultation in history:
            # Filter by query
            if query:
                cons_id = consultation.get('consultation_id', '').lower()
                disease_id = consultation.get('diagnosis', {}).get('conclusion', '').lower()
                if query.lower() not in cons_id and query.lower() not in disease_id:
                    continue
            
            # Filter by disease
            if disease_filter:
                conclusion_id = consultation.get('diagnosis', {}).get('conclusion')
                if conclusion_id != disease_filter:
                    continue
            
            # Filter by date range
            timestamp = consultation.get('timestamp', '')
            if date_from and timestamp < date_from:
                continue
            if date_to and timestamp > date_to:
                continue
            
            results.append(consultation)
        
        return results
    
    def get_statistics(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dapatkan statistik dari list consultation history.
        
        Args:
            history: List of all consultations.
            
        Returns:
            Dictionary berisi berbagai statistik
        """
        if not history:
            return {
                "total_consultations": 0,
                "unique_diseases": 0,
                "top_diseases": [],
                "first_consultation_timestamp": None,
                "last_consultation_timestamp": None,
            }
        
        # Count by disease
        disease_count: Dict[str, int] = {}
        for consultation in history:
            disease_id = consultation.get('diagnosis', {}).get('conclusion')
            if disease_id:
                disease_count[disease_id] = disease_count.get(disease_id, 0) + 1
        
        # Top diseases
        top_diseases = sorted(
            disease_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Enrich dengan disease names
        top_diseases_with_names = []
        for disease_id, count in top_diseases:
            disease = self._get_disease_by_id(disease_id)
            disease_name = 'Unknown'
            if disease:
                disease_name = disease.get('nama', disease.get('name', 'Unknown'))
            
            top_diseases_with_names.append({
                "disease_id": disease_id,
                "disease_name": disease_name,
                "count": count
            })
        
        # Timestamps are already sorted descending in load_consultation_history
        return {
            "total_consultations": len(history),
            "unique_diseases": len(disease_count),
            "top_diseases": top_diseases_with_names,
            "first_consultation_timestamp": history[-1].get('timestamp') if history else None,
            "last_consultation_timestamp": history[0].get('timestamp') if history else None,
        }
    
    def export_to_csv(
        self,
        output_path: Optional[str] = None,
        consultations: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Export consultations ke CSV.
        
        Args:
            output_path: Path output file (auto-generate jika None)
            consultations: List consultations to export (semua jika None)
            
        Returns:
            Path ke file CSV yang dibuat
        """
        import csv
        
        # Auto-generate path jika tidak diberikan
        if output_path is None:
            output_path = os.path.join(
                self.history_dir,
                f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
        
        # Load consultations jika tidak diberikan
        if consultations is None:
            consultations = self.load_consultation_history()
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'timestamp', 'disease_id', 'disease_name', 'cf', 'symptoms_count']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for cons in consultations:
                disease_detail = cons.get('diagnosis', {}).get('conclusion_detail', {})
                disease_name = disease_detail.get('nama', disease_detail.get('name', ''))
                
                writer.writerow({
                    'id': cons.get('id', ''),
                    'timestamp': cons.get('timestamp', ''),
                    'disease_id': cons.get('diagnosis', {}).get('conclusion_id', ''),
                    'disease_name': disease_name,
                    'cf': cons.get('diagnosis', {}).get('cf', 0.0),
                    'symptoms_count': len(cons.get('symptoms', {}).get('ids', []))
                })
        
        return output_path


# Contoh penggunaan
if __name__ == "__main__":
    storage = StorageService()
    
    # Test save consultation
    test_result = {
        "conclusion": "P1",
        "cf": 0.85,
        "method": "forward",
        "used_rules": ["R1", "R2"],
        "reasoning_path": "R1 -> R2",
        "trace": []
    }
    
    cons_id = storage.save_consultation(
        symptom_ids=["G1", "G2"],
        diagnosis_result=test_result,
        user_cf=0.9,
        user_info={"name": "Test User"}
    )
    
    print(f"✅ Consultation saved: {cons_id}")
    
    # Test load history
    history = storage.load_consultation_history(limit=5)
    print(f"✅ Loaded {len(history)} consultations")
    
    # Test statistics
    stats = storage.get_statistics()
    print(f"✅ Statistics: {stats['total_consultations']} total consultations")