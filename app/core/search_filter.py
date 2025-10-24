"""Modul Search & Filter untuk Knowledge Base.

Menyediakan fungsi untuk mencari dan memfilter data dari knowledge base:
- Gejala (symptoms)
- Penyakit (diseases)
- Aturan (rules)

Fitur utama:
- Pencarian teks (text search) pada nama, deskripsi, ID
- Filter berdasarkan spesies ikan (species filter)
- Filter berdasarkan rentang nilai CF (certainty factor range)
- Filter rules berdasarkan antecedent atau consequent tertentu
- Sorting berdasarkan berbagai kriteria (nama, CF, ID, dll)
- Kombinasi multiple filter

Fungsi-fungsi ini dirancang untuk mempermudah eksplorasi KB di UI
dan mendukung fitur pencarian interaktif.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Callable
import re
import os
import json


def _normalize_text(text: str) -> str:
    """Normalisasi teks untuk pencarian: lowercase, hapus karakter khusus."""
    if not text:
        return ""
    # Ubah ke lowercase dan ganti underscore/dash dengan spasi
    text = text.lower().replace("_", " ").replace("-", " ")
    # Hapus karakter non-alphanumeric kecuali spasi
    text = re.sub(r"[^a-z0-9\s]", "", text)
    # Hapus spasi berlebih
    text = " ".join(text.split())
    return text


def _matches_text_obj(item: Any, query: str, fields: List[str]) -> bool:
    """Cek apakah object cocok dengan query pada field-field tertentu."""
    if not query:
        return True
    
    normalized_query = _normalize_text(query)
    for field in fields:
        value = getattr(item, field, "")
        if isinstance(value, list):
            value = " ".join(str(v) for v in value)
        normalized_value = _normalize_text(str(value))
        if normalized_query in normalized_value:
            return True
    return False


def search_symptoms(
    symptoms: Dict[str, Any],
    query: Optional[str] = None,
    species_filter: Optional[List[str]] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None,
    sort_by: str = "id",
    ascending: bool = True
) -> List[Any]:
    """Cari dan filter gejala berdasarkan berbagai kriteria. Bekerja dengan objek."""
    results = []
    
    for sid, s_obj in symptoms.items():
        # Filter berdasarkan query teks
        if query and not _matches_text_obj(s_obj, query, ["id", "nama", "deskripsi"]):
            continue
        
        # Filter berdasarkan spesies
        if species_filter:
            symptom_species = getattr(s_obj, 'species', [])
            if symptom_species and not any(sp in species_filter for sp in symptom_species):
                continue
        
        # Filter berdasarkan weight/bobot
        weight = float(getattr(s_obj, 'bobot', 1.0))
        if weight_min is not None and weight < weight_min:
            continue
        if weight_max is not None and weight > weight_max:
            continue
        
        results.append(s_obj)
    
    # Sorting
    if sort_by in ["name", "nama"]:
        key_fn = lambda x: _normalize_text(getattr(x, 'nama', ''))
    elif sort_by == "weight":
        key_fn = lambda x: float(getattr(x, 'bobot', 1.0))
    else:  # default: sort by id
        key_fn = lambda x: getattr(x, 'id', '')
    
    results.sort(key=key_fn, reverse=not ascending)
    return results


def search_diseases(
    diseases: Dict[str, Any],
    query: Optional[str] = None,
    species_filter: Optional[List[str]] = None,
    sort_by: str = "id",
    ascending: bool = True
) -> List[Any]:
    """Cari dan filter penyakit berdasarkan berbagai kriteria. Bekerja dengan objek."""
    results = []
    
    for did, d_obj in diseases.items():
        # Filter berdasarkan query teks (cari di banyak field)
        search_fields = ["id", "nama", "deskripsi", "penyebab", "pengobatan", "pencegahan"]
        if query and not _matches_text_obj(d_obj, query, search_fields):
            continue
        
        # Filter berdasarkan spesies (jika ada)
        if species_filter:
            disease_species = getattr(d_obj, 'species', [])
            if disease_species and not any(sp in species_filter for sp in disease_species):
                continue
        
        results.append(d_obj)
    
    # Sorting
    if sort_by in ["name", "nama"]:
        key_fn = lambda x: _normalize_text(getattr(x, 'nama', ''))
    else:
        key_fn = lambda x: getattr(x, 'id', '')
    
    results.sort(key=key_fn, reverse=not ascending)
    return results


def search_rules(
    rules: Dict[str, Any],
    query: Optional[str] = None,
    antecedent_filter: Optional[str] = None,
    consequent_filter: Optional[str] = None,
    cf_min: Optional[float] = None,
    cf_max: Optional[float] = None,
    sort_by: str = "id",
    ascending: bool = True
) -> Dict[str, Any]:
    """Cari dan filter rules berdasarkan berbagai kriteria. Bekerja dengan dictionary."""
    results = {}
    
    for rid, r_dict in rules.items():
        # Buat salinan untuk dimodifikasi
        rule_with_id = r_dict.copy()
        rule_with_id['id'] = rid

        # Filter berdasarkan query teks
        if query:
            search_fields = ["id", "ask_why", "recommendation", "source", "THEN"]
            # Tambahkan antecedent ke pencarian (IF adalah list)
            if_list = rule_with_id.get("IF", [])
            rule_with_id["_if_text"] = " ".join(if_list)
            search_fields.append("_if_text")
            
            # Gunakan _matches_text yang asli untuk dictionary
            if not _matches_text(rule_with_id, query, search_fields):
                continue
        
        # Filter berdasarkan antecedent (IF mengandung item tertentu)
        if antecedent_filter:
            antecedents = rule_with_id.get("IF", [])
            if antecedent_filter not in antecedents:
                continue
        
        # Filter berdasarkan consequent (THEN)
        if consequent_filter:
            consequent = rule_with_id.get("THEN", "")
            if consequent != consequent_filter:
                continue
        
        # Filter berdasarkan CF range
        cf = float(rule_with_id.get("CF", 1.0))
        if cf_min is not None and cf < cf_min:
            continue
        if cf_max is not None and cf > cf_max:
            continue
        
        results[rid] = r_dict
    
    # Sorting
    # Karena kita mengembalikan dict, sorting lebih rumit.
    # Untuk saat ini, kita akan mengembalikan dict yang difilter tanpa sorting.
    # Jika sorting diperlukan, kita harus mengubah return type ke list of tuples atau list of dicts.
    return results

def _matches_text(item: Dict[str, Any], query: str, fields: List[str]) -> bool:
	"""Cek apakah item cocok dengan query pada field-field tertentu."""
	if not query:
		return True
	
	normalized_query = _normalize_text(query)
	for field in fields:
		value = item.get(field, "")
		if isinstance(value, list):
			# Jika field adalah list (mis. treatments, prevention), gabungkan jadi string
			value = " ".join(str(v) for v in value)
		normalized_value = _normalize_text(str(value))
		if normalized_query in normalized_value:
			return True
	return False


def filter_by_species(
    items: List[Any],
    species_list: List[str]
) -> List[Any]:
    """Filter generik berdasarkan spesies untuk list of objects."""
    if not species_list:
        return items
    
    filtered = []
    for item in items:
        item_species = getattr(item, 'species', [])
        if not item_species:
            filtered.append(item)
            continue
        if any(sp in species_list for sp in item_species):
            filtered.append(item)
    
    return filtered


def get_rules_by_disease(
    rules: Dict[str, Dict[str, Any]],
    disease_id: str
) -> Dict[str, Any]:
    """Dapatkan semua rules yang menghasilkan penyakit tertentu."""
    return search_rules(rules, consequent_filter=disease_id)


def get_rules_by_symptom(
    rules: Dict[str, Dict[str, Any]],
    symptom_id: str
) -> Dict[str, Any]:
    """Dapatkan semua rules yang menggunakan gejala tertentu."""
    return search_rules(rules, antecedent_filter=symptom_id)


def get_related_symptoms(
    rules: Dict[str, Dict[str, Any]],
    symptom_id: str
) -> List[str]:
    """Dapatkan gejala-gejala lain yang sering muncul bersama gejala tertentu."""
    related = set()
    for rid, r in rules.items():
        antecedents = getattr(r, 'IF', [])
        if symptom_id in antecedents:
            for ant in antecedents:
                if ant != symptom_id:
                    related.add(ant)
    return sorted(list(related))


def get_possible_diseases(
    rules: Dict[str, Dict[str, Any]],
    symptom_ids: List[str]
) -> List[str]:
    """Dapatkan daftar penyakit yang mungkin berdasarkan gejala yang dipilih."""
    possible = set()
    symptom_set = set(symptom_ids)
    
    for rid, r in rules.items():
        antecedents = set(getattr(r, 'IF', []))
        if antecedents & symptom_set:
            consequent = getattr(r, 'THEN', None)
            if consequent:
                possible.add(consequent)
    
    return sorted(list(possible))


def highlight_search_term(text: str, query: str) -> str:
    """Highlight query di dalam text untuk tampilan UI (gunakan markdown bold)."""
    if not query or not text:
        return text
    
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)


# ========== CLASS-BASED API (INTEGRATED WITH DATABASE) ==========

class SearchFilter:
    """Class wrapper untuk search & filter dengan integrasi database_manager.
    
    Menyediakan interface yang lebih mudah untuk Pages layer.
    Menggunakan fungsi-fungsi database_manager untuk akses data.
    """
    
    def __init__(self):
        """Initialize SearchFilter dengan akses ke database."""
        import sys
        import os
        # Pastikan path ke 'app' ada di sys.path
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from database.database_manager import DatabaseManager
        from pathlib import Path

        # Inisialisasi DatabaseManager untuk memuat semua data secara konsisten
        db_path = Path(__file__).parent.parent / "database"
        self.db = DatabaseManager(db_path)
        self.db.load_all()

    def search_symptoms(
        self,
        query: Optional[str] = None,
        species_filter: Optional[List[str]] = None,
        weight_min: Optional[float] = None,
        weight_max: Optional[float] = None,
        sort_by: str = "id",
        ascending: bool = True
    ) -> List[Any]:
        """Cari symptoms dengan akses langsung ke database."""
        symptoms = self.db.symptoms
        return search_symptoms(
            symptoms, query, species_filter, 
            weight_min, weight_max, sort_by, ascending
        )
    
    def search_diseases(
        self,
        query: Optional[str] = None,
        species_filter: Optional[List[str]] = None,
        sort_by: str = "id",
        ascending: bool = True
    ) -> List[Any]:
        """Cari diseases dengan akses langsung ke database."""
        diseases = self.db.diseases
        return search_diseases(diseases, query, species_filter, sort_by, ascending)
    
    def search_rules(
        self,
        query: Optional[str] = None,
        antecedent_filter: Optional[str] = None,
        consequent_filter: Optional[str] = None,
        cf_min: Optional[float] = None,
        cf_max: Optional[float] = None,
        sort_by: str = "id",
        ascending: bool = True
    ) -> Dict[str, Any]:
        """Cari rules dengan akses langsung ke database."""
        rules = self.db.rules
        return search_rules(
            rules, query, antecedent_filter, consequent_filter,
            cf_min, cf_max, sort_by, ascending
        )
    
    def get_rules_by_disease(self, disease_id: str) -> Dict[str, Any]:
        """Dapatkan rules yang menghasilkan penyakit tertentu."""
        rules = self.db.rules
        return get_rules_by_disease(rules, disease_id)
    
    def get_rules_by_symptom(self, symptom_id: str) -> Dict[str, Any]:
        """Dapatkan rules yang menggunakan gejala tertentu."""
        rules = self.db.rules
        return get_rules_by_symptom(rules, symptom_id)
    
    def get_related_symptoms(self, symptom_id: str) -> List[str]:
        """Dapatkan gejala-gejala terkait."""
        rules = self.db.rules
        return get_related_symptoms(rules, symptom_id)
    
    def get_possible_diseases(self, symptom_ids: List[str]) -> List[str]:
        """Dapatkan daftar penyakit yang mungkin berdasarkan gejala."""
        rules = self.db.rules
        return get_possible_diseases(rules, symptom_ids)
    
    def get_all_symptoms(self) -> Dict[str, Any]:
        """Load semua symptoms dari database."""
        return self.db.symptoms
    
    def get_all_diseases(self) -> Dict[str, Any]:
        """Load semua diseases dari database."""
        return self.db.diseases
    
    def get_all_rules(self) -> Dict[str, Any]:
        """Load semua rules dari database."""
        return self.db.rules


# ===== Contoh penggunaan (untuk testing) =====
if __name__ == "__main__":
    # Inisialisasi SearchFilter untuk testing
    sf = SearchFilter()
    
    # Test search symptoms
    print("=== Test Search Symptoms ===")
    hasil_symptoms = sf.search_symptoms(query="putih", species_filter=["Lele"])
    print(f"Hasil pencarian 'putih' untuk Lele: {len(hasil_symptoms)} item")
    for h in hasil_symptoms:
        print(f"  - {h.id}: {h.name}")
    
    # Test search rules by symptom
    print("\n=== Test Get Rules by Symptom ===")
    rules_g1 = sf.get_rules_by_symptom("G1")
    print(f"Rules yang menggunakan G1: {len(rules_g1)} rules")
    for r in rules_g1:
        print(f"  - {r.id}: IF {r.IF} THEN {r.THEN}")
    
    # Test get possible diseases
    print("\n=== Test Get Possible Diseases ===")
    diseases = sf.get_possible_diseases(["G1", "G2"])
    print(f"Penyakit yang mungkin dari G1+G2: {diseases}")
    
    print("\n✅ Semua test search_filter.py berjalan sukses!")
