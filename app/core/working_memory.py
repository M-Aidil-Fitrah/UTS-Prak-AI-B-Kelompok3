"""
Working Memory Module
Menyimpan fakta-fakta dan hasil inferensi selama proses diagnosis
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Fact:
    """Representasi satu fakta dalam working memory"""
    fact_id: str
    fact_type: str  # 'symptom' atau 'disease'
    value: any
    cf: float = 1.0  # Certainty Factor
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "user"  # 'user' atau 'inference'

class WorkingMemory:
    """
    Working Memory untuk menyimpan state diagnosis saat ini
    Menyimpan gejala yang dipilih user dan hasil inferensi
    """
    
    def __init__(self):
        self.facts: Dict[str, Fact] = {}
        self.inferred_diseases: Dict[str, float] = {}  # disease_id -> CF
        self.fired_rules: List[str] = []  # Rule yang sudah dieksekusi
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metadata: Dict = {
            "start_time": datetime.now(),
            "user_symptoms_count": 0,
            "inference_count": 0
        }
    
    def add_symptom(self, symptom_id: str, cf: float = 1.0) -> None:
        """
        Menambahkan gejala yang dipilih user ke working memory
        
        Args:
            symptom_id: ID gejala (misal: G1, G2)
            cf: Certainty Factor dari user (default 1.0)
        """
        fact = Fact(
            fact_id=symptom_id,
            fact_type="symptom",
            value=True,
            cf=cf,
            source="user"
        )
        self.facts[symptom_id] = fact
        self.metadata["user_symptoms_count"] += 1
    
    def add_symptoms_batch(self, symptom_ids: List[str], cf: float = 1.0) -> None:
        """Menambahkan beberapa gejala sekaligus"""
        for symptom_id in symptom_ids:
            self.add_symptom(symptom_id, cf)
    
    def has_symptom(self, symptom_id: str) -> bool:
        """Cek apakah gejala ada di working memory"""
        return symptom_id in self.facts and self.facts[symptom_id].fact_type == "symptom"
    
    def get_symptom_cf(self, symptom_id: str) -> float:
        """Ambil CF dari gejala tertentu"""
        if self.has_symptom(symptom_id):
            return self.facts[symptom_id].cf
        return 0.0
    
    def get_all_symptoms(self) -> List[str]:
        """Ambil semua ID gejala yang ada di working memory"""
        return [fid for fid, fact in self.facts.items() if fact.fact_type == "symptom"]
    
    def add_inferred_disease(self, disease_id: str, cf: float) -> None:
        """
        Menambahkan hasil inferensi penyakit
        Jika penyakit sudah ada, gabungkan CF-nya
        
        Args:
            disease_id: ID penyakit (misal: P1, P2)
            cf: Certainty Factor hasil inferensi
        """
        if disease_id in self.inferred_diseases:
            # Kombinasi CF jika penyakit sudah pernah diinfer
            old_cf = self.inferred_diseases[disease_id]
            self.inferred_diseases[disease_id] = self._combine_cf(old_cf, cf)
        else:
            self.inferred_diseases[disease_id] = cf
        
        self.metadata["inference_count"] += 1
    
    def _combine_cf(self, cf1: float, cf2: float) -> float:
        """
        Kombinasi dua CF menggunakan rumus Certainty Factor
        CF(A,B) = CF(A) + CF(B) * (1 - CF(A))
        
        Args:
            cf1: CF pertama
            cf2: CF kedua
            
        Returns:
            CF gabungan
        """
        if cf1 > 0 and cf2 > 0:
            return cf1 + cf2 * (1 - cf1)
        elif cf1 < 0 and cf2 < 0:
            return cf1 + cf2 * (1 + cf1)
        else:
            return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))
    
    def mark_rule_fired(self, rule_id: str) -> None:
        """Tandai rule sudah dieksekusi (untuk menghindari loop)"""
        if rule_id not in self.fired_rules:
            self.fired_rules.append(rule_id)
    
    def is_rule_fired(self, rule_id: str) -> bool:
        """Cek apakah rule sudah pernah dieksekusi"""
        return rule_id in self.fired_rules
    
    def get_diagnosis_results(self) -> List[Dict]:
        """
        Ambil hasil diagnosis yang sudah diurutkan berdasarkan CF tertinggi
        
        Returns:
            List of dict dengan format: [{'disease_id': 'P1', 'cf': 0.85}, ...]
        """
        results = [
            {"disease_id": did, "cf": cf}
            for did, cf in self.inferred_diseases.items()
        ]
        # Urutkan berdasarkan CF dari tinggi ke rendah
        results.sort(key=lambda x: x["cf"], reverse=True)
        return results
    
    def get_top_disease(self) -> Optional[Dict]:
        """Ambil penyakit dengan CF tertinggi"""
        results = self.get_diagnosis_results()
        return results[0] if results else None
    
    def clear(self) -> None:
        """Reset working memory (untuk diagnosis baru)"""
        self.facts.clear()
        self.inferred_diseases.clear()
        self.fired_rules.clear()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metadata = {
            "start_time": datetime.now(),
            "user_symptoms_count": 0,
            "inference_count": 0
        }
    
    def get_summary(self) -> Dict:
        """Ambil ringkasan working memory untuk debugging/logging"""
        return {
            "session_id": self.session_id,
            "symptoms_count": len(self.get_all_symptoms()),
            "diseases_inferred": len(self.inferred_diseases),
            "rules_fired": len(self.fired_rules),
            "top_disease": self.get_top_disease(),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"WorkingMemory(symptoms={len(self.get_all_symptoms())}, diseases={len(self.inferred_diseases)}, session={self.session_id})"