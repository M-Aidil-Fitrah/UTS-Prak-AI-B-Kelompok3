
"""
Working Memory untuk menyimpan fakta-fakta sementara selama inferensi.

Modul ini mengelola:
- Fakta yang diketahui dan CF-nya
- Update fakta baru dari hasil inferensi
- History perubahan fakta
- Query fakta berdasarkan kriteria
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FactEntry:
    """Representasi satu fakta dalam working memory."""
    fact_id: str
    cf: float
    source: str  # "user_input" | "rule_R1" | "rule_R2" 
    timestamp: datetime = field(default_factory=datetime.now)
    derived_from: Optional[List[str]] = None  # Daftar fakta antecedent


class WorkingMemory:
    """Manajemen working memory untuk inference engine.
    
    Working memory menyimpan:
    1. Fakta awal dari user input
    2. Fakta derived dari inferensi
    3. History perubahan CF untuk setiap fakta
    """
    
    def __init__(self):
        self.facts_cf: Dict[str, float] = {}
        self.facts_history: Dict[str, List[FactEntry]] = {}
        self.facts_source: Dict[str, str] = {}
    
    def add_initial_facts(self, facts: Dict[str, float]) -> None:
        """Tambahkan fakta awal dari user input."""
        for fact_id, cf in facts.items():
            self.add_fact(fact_id, cf, source="user_input")
    
    def add_fact(
        self, 
        fact_id: str, 
        cf: float, 
        source: str = "inference",
        derived_from: Optional[List[str]] = None
    ) -> float:
        """Tambahkan atau update fakta.
        
        Returns:
            delta_cf: Perubahan CF (untuk tracking)
        """
        old_cf = self.facts_cf.get(fact_id, 0.0)
        new_cf = self._combine_cf(old_cf, cf)
        delta = new_cf - old_cf
        
        # Update fakta
        self.facts_cf[fact_id] = new_cf
        self.facts_source[fact_id] = source
        
        # Simpan history
        entry = FactEntry(
            fact_id=fact_id,
            cf=new_cf,
            source=source,
            derived_from=derived_from
        )
        if fact_id not in self.facts_history:
            self.facts_history[fact_id] = []
        self.facts_history[fact_id].append(entry)
        
        return delta
    
    def get_fact(self, fact_id: str) -> Optional[float]:
        """Ambil CF dari fakta."""
        return self.facts_cf.get(fact_id)
    
    def has_fact(self, fact_id: str, min_cf: float = 0.0) -> bool:
        """Cek apakah fakta ada dengan CF minimal."""
        return self.facts_cf.get(fact_id, 0.0) > min_cf
    
    def has_all_facts(self, fact_ids: List[str], min_cf: float = 0.0) -> bool:
        """Cek apakah semua fakta ada."""
        return all(self.has_fact(fid, min_cf) for fid in fact_ids)
    
    def get_facts_set(self) -> Set[str]:
        """Ambil set semua fakta yang ada."""
        return set(self.facts_cf.keys())
    
    def get_facts_above_threshold(self, threshold: float) -> Dict[str, float]:
        """Ambil fakta dengan CF di atas threshold."""
        return {
            fid: cf 
            for fid, cf in self.facts_cf.items() 
            if cf >= threshold
        }
    
    def get_history(self, fact_id: str) -> List[FactEntry]:
        """Ambil history perubahan fakta."""
        return self.facts_history.get(fact_id, [])
    
    def clear(self) -> None:
        """Reset working memory."""
        self.facts_cf.clear()
        self.facts_history.clear()
        self.facts_source.clear()
    
    def to_dict(self) -> Dict[str, any]:
        """Export working memory untuk debugging/logging."""
        return {
            "facts": self.facts_cf,
            "sources": self.facts_source,
            "count": len(self.facts_cf)
        }
    
    @staticmethod
    def _combine_cf(cf_old: float, cf_new: float) -> float:
        """Combine CF menggunakan MYCIN formula."""
        # Pindah dari inference_engine.py
        cf_old = max(0.0, min(1.0, cf_old))
        cf_new = max(0.0, min(1.0, cf_new))
        return max(0.0, min(1.0, cf_old + cf_new * (1.0 - cf_old)))
