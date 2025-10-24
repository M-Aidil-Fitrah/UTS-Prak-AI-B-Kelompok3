import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class Symptom:
    """Model untuk Symptom."""
    def __init__(self, id: str, nama: str, deskripsi: str = "", species: Optional[List[str]] = None):
        self.id = id
        self.name = nama
        self.nama = nama
        self.description = deskripsi
        self.deskripsi = deskripsi
        self.species = species or []


class Disease:
    """Model untuk Disease."""
    def __init__(self, id: str, nama: str, penyebab: str = "", deskripsi: str = "", 
                 pengobatan: str = "", pencegahan: str = ""):
        self.id = id
        self.name = nama
        self.nama = nama
        self.penyebab = penyebab
        self.deskripsi = deskripsi
        self.pengobatan = pengobatan
        self.pencegahan = pencegahan


class DatabaseManager:
    """Manager untuk mengakses database symptoms, diseases, dan rules."""
    
    def __init__(self, db_path: Path):
        """Initialize DatabaseManager dengan path ke folder database.
        
        Args:
            db_path: Path object menuju folder database
        """
        self.db_path = Path(db_path)
        self.symptoms: Dict[str, Symptom] = {}
        self.diseases: Dict[str, Disease] = {}
        self.rules: Dict[str, Dict[str, Any]] = {}
    
    def load_all(self):
        """Load semua data dari database files."""
        self.load_symptoms()
        self.load_diseases()
        self.load_rules()
    
    def load_symptoms(self):
        """Load symptoms dari symptoms.json."""
        symptoms_file = self.db_path / "symptoms.json"
        if not symptoms_file.exists():
            raise FileNotFoundError(f"Symptoms file not found: {symptoms_file}")
        
        with open(symptoms_file, 'r', encoding='utf-8') as f:
            symptoms_data = json.load(f)
        
        self.symptoms = {}
        for item in symptoms_data:
            symptom = Symptom(
                id=item['id'],
                nama=item['nama'],
                deskripsi=item.get('deskripsi', ''),
                species=item.get('species', [])
            )
            self.symptoms[symptom.id] = symptom
    
    def load_diseases(self):
        """Load diseases dari diseases.json."""
        diseases_file = self.db_path / "diseases.json"
        if not diseases_file.exists():
            raise FileNotFoundError(f"Diseases file not found: {diseases_file}")
        
        with open(diseases_file, 'r', encoding='utf-8') as f:
            diseases_data = json.load(f)
        
        self.diseases = {}
        for item in diseases_data:
            disease = Disease(
                id=item['id'],
                nama=item['nama'],
                penyebab=item.get('penyebab', ''),
                deskripsi=item.get('deskripsi', ''),
                pengobatan=item.get('pengobatan', ''),
                pencegahan=item.get('pencegahan', '')
            )
            self.diseases[disease.id] = disease
    
    def load_rules(self):
        """Load rules dari rules.json. Mendukung format list atau dict."""
        rules_file = self.db_path / "rules.json"
        if not rules_file.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_file}")
        
        with open(rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Jika data adalah list, konversi ke dict
        if isinstance(data, list):
            self.rules = {rule.get("id", f"rule_{i}"): rule for i, rule in enumerate(data)}
        # Jika sudah dict, gunakan langsung
        else:
            self.rules = data
    
    def get_symptom(self, symptom_id: str) -> Optional[Symptom]:
        """Get symptom by ID."""
        return self.symptoms.get(symptom_id)
    
    def get_disease(self, disease_id: str) -> Optional[Disease]:
        """Get disease by ID."""
        return self.diseases.get(disease_id)
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get rule by ID."""
        return self.rules.get(rule_id)

    def save_symptoms(self):
        """Save symptoms kembali ke symptoms.json."""
        symptoms_file = self.db_path / "symptoms.json"
        symptoms_list = [
            {
                "id": s.id,
                "nama": s.nama,
                "deskripsi": s.deskripsi,
                "species": s.species
            } for s in self.symptoms.values()
        ]
        with open(symptoms_file, 'w', encoding='utf-8') as f:
            json.dump(symptoms_list, f, indent=4, ensure_ascii=False)

    def add_symptom(self, sid: str, name: str, desc: str, species: List[str]):
        """Menambahkan gejala baru."""
        if sid in self.symptoms:
            raise ValueError(f"Symptom dengan ID '{sid}' sudah ada.")
        
        new_symptom = Symptom(id=sid, nama=name, deskripsi=desc, species=species)
        self.symptoms[sid] = new_symptom
        self.save_symptoms()

    def save_diseases(self):
        """Save diseases kembali ke diseases.json."""
        diseases_file = self.db_path / "diseases.json"
        diseases_list = [
            {
                "id": d.id,
                "nama": d.nama,
                "penyebab": d.penyebab,
                "deskripsi": d.deskripsi,
                "pengobatan": d.pengobatan,
                "pencegahan": d.pencegahan
            } for d in self.diseases.values()
        ]
        with open(diseases_file, 'w', encoding='utf-8') as f:
            json.dump(diseases_list, f, indent=4, ensure_ascii=False)

    def add_disease(self, did: str, name: str, desc: str, cause: str, treatments: str, prevention: str):
        """Menambahkan penyakit baru."""
        if did in self.diseases:
            raise ValueError(f"Disease dengan ID '{did}' sudah ada.")
            
        new_disease = Disease(
            id=did, 
            nama=name, 
            deskripsi=desc, 
            penyebab=cause, 
            pengobatan=treatments, 
            pencegahan=prevention
        )
        self.diseases[did] = new_disease
        self.save_diseases()
    
    def save_rules(self):
        """Save rules kembali ke rules.json."""
        rules_file = self.db_path / "rules.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, indent=4, ensure_ascii=False)
    
    def add_rule(self, rule_id: str, symptoms: List[str], disease_id: str, cf: float):
        """Menambahkan rule baru."""
        self.rules[rule_id] = {"IF": symptoms, "THEN": disease_id, "CF": cf}
        self.save_rules()
    
    def edit_rule(self, rule_id: str, symptoms: Optional[List[str]] = None, 
                  disease_id: Optional[str] = None, cf: Optional[float] = None):
        """Mengedit rule yang sudah ada."""
        if rule_id not in self.rules:
            raise ValueError(f"Rule {rule_id} tidak ditemukan.")
        
        if symptoms is not None:
            self.rules[rule_id]["IF"] = symptoms
        if disease_id is not None:
            self.rules[rule_id]["THEN"] = disease_id
        if cf is not None:
            self.rules[rule_id]["CF"] = cf
        
        self.save_rules()
    
    def delete_rule(self, rule_id: str):
        """Menghapus rule dari file."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.save_rules()
        else:
            raise ValueError(f"Rule {rule_id} tidak ditemukan.")


# Legacy functions untuk backward compatibility
RULES_PATH = "database/rules.json"

def load_rules():
    """Memuat seluruh rules dari file JSON. Mendukung format list atau dict."""
    if not os.path.exists(RULES_PATH):
        return {}
    with open(RULES_PATH, "r") as f:
        data = json.load(f)
    
    # Jika data adalah list, konversi ke dict
    if isinstance(data, list):
        return {rule.get("id", f"rule_{i}"): rule for i, rule in enumerate(data)}
    
    # Jika sudah dict, kembalikan langsung
    return data

def save_rules(rules):
    """Menyimpan rules baru ke file JSON"""
    with open(RULES_PATH, "w") as f:
        json.dump(rules, f, indent=4)

def add_rule(rule_id, symptoms, disease_id, cf):
    """Menambahkan rule baru"""
    rules = load_rules()
    rules[rule_id] = {"IF": symptoms, "THEN": disease_id, "CF": cf}
    save_rules(rules)
    print(f"Rule {rule_id} berhasil ditambahkan.")

def edit_rule(rule_id, symptoms=None, disease_id=None, cf=None):
    """Mengedit rule yang sudah ada"""
    rules = load_rules()
    if rule_id not in rules:
        print(f"Rule {rule_id} tidak ditemukan.")
        return
    if symptoms:
        rules[rule_id]["IF"] = symptoms
    if disease_id:
        rules[rule_id]["THEN"] = disease_id
    if cf is not None:
        rules[rule_id]["CF"] = cf
    save_rules(rules)
    print(f"Rule {rule_id} berhasil diperbarui.")

def delete_rule(rule_id):
    """Menghapus rule dari file"""
    rules = load_rules()
    if rule_id in rules:
        del rules[rule_id]
        save_rules(rules)
        print(f"Rule {rule_id} berhasil dihapus.")
    else:
        print(f"Rule {rule_id} tidak ditemukan.")

if __name__ == "__main__":
    # Contoh penggunaan
    add_rule("R4", ["G6", "G8"], "P2", 0.75)
