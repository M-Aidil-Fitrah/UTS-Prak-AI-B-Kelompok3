# File: core/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Symptom:
    """Mewakili satu gejala yang dapat diamati."""
    id: str
    name: str # 'name' dan 'question' bisa tetap Inggris karena ini lebih ke internal
    question: str

@dataclass
class Disease:
    """Mewakili satu jenis penyakit ikan."""
    id: str
    nama: str  # <-- Diubah dari 'name'
    penyebab: str  # <-- Diubah dari 'cause'
    deskripsi: str  # <-- Diubah dari 'description'
    pengobatan: str  # <-- Diubah dari 'treatment'
    pencegahan: str  # <-- Diubah dari 'prevention'

@dataclass
class Rule:
    """Mewakili satu aturan IF-THEN dalam knowledge base."""
    id: str
    IF: List[str]
    THEN: str
    CF: float

@dataclass
class Fact:
    """Mewakili sebuah fakta yang diketahui, biasanya dari input user."""
    symptom_id: str
    user_cf: float

@dataclass
class DiagnosisResult:
    """Mewakili hasil akhir diagnosis untuk satu penyakit."""
    disease: Disease
    final_cf: float
    reasoning_path: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # Format CF menjadi persentase untuk kemudahan pembacaan
        self.confidence_percent: float = round(self.final_cf * 100, 2)
        
        
@dataclass
class KnowledgeBase:
    """Wadah untuk semua data knowledge base yang dimuat."""
    rules: Dict[str, Rule]
    symptoms: Dict[str, Symptom]
    diseases: Dict[str, Disease]        
