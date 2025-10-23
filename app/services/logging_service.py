# services/logging_service.py

"""
Menyediakan layanan logging terpusat untuk aplikasi dengan integrasi database.

Modul ini mengkonfigurasi logger standar menggunakan library logging
bawaan Python dan menyediakan LoggingService untuk:
- Log diagnosis sessions
- Track rule usage statistics  
- Generate system statistics
- Integration dengan database_manager

Penggunaan RotatingFileHandler memastikan file log tidak membengkak
tanpa batas.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import database functions untuk integrasi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database_manager import load_rules

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


class LoggingService:
    """Service untuk logging dan statistics dengan integrasi database.
    
    Menyediakan fungsi untuk:
    - Log diagnosis sessions
    - Track rule usage (in-memory statistics)
    - Generate statistics
    - System monitoring
    """
    
    def __init__(self, logger_name: str = 'ExpertSystemLogger'):
        """Initialize LoggingService.
        
        Args:
            logger_name: Nama logger yang akan digunakan
        """
        self.logger = setup_logger(logger_name)
        self._rule_usage: Dict[str, int] = {}  # In-memory tracking
        
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
    
    def _get_disease_by_id(self, disease_id: str) -> Optional[Dict[str, Any]]:
        """Ambil detail disease dari database."""
        diseases = self._load_json(self.diseases_path)
        return diseases.get(disease_id)
    
    def log_diagnosis(
        self,
        symptom_ids: List[str],
        result: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log diagnosis session dan update rule usage statistics.
        
        Args:
            symptom_ids: List ID gejala yang dipilih
            result: Hasil diagnosis dari inference engine
            user_info: Info tambahan user (optional)
        """
        # Log basic info
        conclusion = result.get('conclusion', 'None')
        cf = result.get('cf', 0.0)
        method = result.get('method', 'unknown')
        
        self.logger.info(
            f"Diagnosis: {len(symptom_ids)} symptoms → "
            f"{conclusion} (CF: {cf:.2f}, Method: {method})"
        )
        
        # Log used rules
        used_rules = result.get('used_rules', [])
        if used_rules:
            self.logger.info(f"Used rules: {', '.join(used_rules)}")
            
            # Track rule usage in-memory
            for rule_id in used_rules:
                if rule_id not in self._rule_usage:
                    self._rule_usage[rule_id] = 0
                self._rule_usage[rule_id] += 1
        
        # Log user info jika ada
        if user_info:
            self.logger.info(f"User info: {user_info}")
    
    def log_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """Log error message.
        
        Args:
            error_msg: Error message
            exception: Exception object (optional)
        """
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_msg)
    
    def log_info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Dapatkan statistik penggunaan sistem.
        
        Returns:
            Dictionary berisi berbagai statistik
        """
        # Load data dari database
        rules = load_rules()
        symptoms = self._load_json(self.symptoms_path)
        diseases = self._load_json(self.diseases_path)
        
        # Get rule usage statistics (sorted)
        rule_usage = sorted(
            [{"rule_id": rid, "usage_count": count} for rid, count in self._rule_usage.items()],
            key=lambda x: x['usage_count'],
            reverse=True
        )[:10]
        
        # Enrich rule usage dengan rule details
        enriched_rule_usage = []
        for item in rule_usage:
            rule_id = item['rule_id']
            rule = rules.get(rule_id, {})
            
            disease_id = rule.get('THEN', '')
            disease = self._get_disease_by_id(disease_id)
            disease_name = 'Unknown'
            if disease:
                disease_name = disease.get('nama', disease.get('name', 'Unknown'))
            
            enriched_rule_usage.append({
                "rule_id": rule_id,
                "usage_count": item['usage_count'],
                "disease_id": disease_id,
                "disease_name": disease_name,
                "rule_cf": rule.get('CF', 0.0)
            })
        
        return {
            "total_rules": len(rules),
            "total_symptoms": len(symptoms),
            "total_diseases": len(diseases),
            "most_used_rules": enriched_rule_usage,
            "log_file": LOG_FILE,
            "log_file_exists": os.path.exists(LOG_FILE),
            "log_file_size": os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_most_used_rules(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Dapatkan rules yang paling sering digunakan.
        
        Args:
            top_n: Jumlah top rules
            
        Returns:
            List dictionary rule usage dengan details
        """
        rules = load_rules()
        
        # Sort by usage
        sorted_usage = sorted(
            self._rule_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        enriched = []
        for rule_id, count in sorted_usage:
            rule = rules.get(rule_id, {})
            
            disease_id = rule.get('THEN', '')
            disease = self._get_disease_by_id(disease_id)
            disease_name = 'Unknown'
            if disease:
                disease_name = disease.get('nama', disease.get('name', 'Unknown'))
            
            enriched.append({
                "rule_id": rule_id,
                "usage_count": count,
                "disease_id": disease_id,
                "disease_name": disease_name,
                "cf": rule.get('CF', 0.0),
                "symptoms_count": len(rule.get('IF', []))
            })
        
        return enriched
    
    def log_knowledge_acquisition(
        self,
        action: str,
        rule_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log knowledge acquisition activities (add/edit/delete rules).
        
        Args:
            action: Tipe aksi ('add', 'edit', 'delete')
            rule_id: ID rule yang dimodifikasi
            details: Detail tambahan (optional)
        """
        self.logger.info(
            f"Knowledge Acquisition: {action.upper()} rule {rule_id}"
        )
        
        if details:
            self.logger.info(f"Details: {details}")
    
    def clear_statistics(self) -> None:
        """Reset rule usage statistics.
        
        WARNING: Ini akan menghapus semua tracking rule usage!
        """
        self._rule_usage = {}
        self.logger.warning("Rule usage statistics cleared!")


# Contoh penggunaan
if __name__ == "__main__":
    logging_service = LoggingService()
    
    # Test log diagnosis
    test_result = {
        "conclusion": "P1",
        "cf": 0.85,
        "method": "forward",
        "used_rules": ["R1", "R2", "R3"],
        "trace": []
    }
    
    logging_service.log_diagnosis(
        symptom_ids=["G1", "G2", "G3"],
        result=test_result,
        user_info={"name": "Test User"}
    )
    
    print("✅ Diagnosis logged")
    
    # Test get statistics
    stats = logging_service.get_statistics()
    print(f"✅ Statistics: {stats['total_rules']} rules, {stats['total_diseases']} diseases")
    
    # Test get most used rules
    most_used = logging_service.get_most_used_rules(top_n=3)
    print(f"✅ Most used rules: {len(most_used)} rules")
    for rule in most_used:
        print(f"  - {rule['rule_id']}: {rule['disease_name']} ({rule['usage_count']} times)")