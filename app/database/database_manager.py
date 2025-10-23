import json
import os
from pathlib import Path

RULES_PATH = "database/rules.json"

class DatabaseManager:
    def __init__(self, database_path):
        """Inisialisasi DatabaseManager dengan path ke folder database"""
        if isinstance(database_path, str):
            database_path = Path(database_path)
        self.database_path = database_path
        self.symptoms = {}
        self.diseases = {}
        self.rules = {}
    
    def load_all(self):
        """Memuat semua data dari file JSON"""
        self.load_symptoms()
        self.load_diseases()
        self.load_rules()
    
    def load_symptoms(self):
        """Memuat data gejala dari symptoms.json"""
        symptoms_file = self.database_path / "symptoms.json"
        if symptoms_file.exists():
            with open(symptoms_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    # Buat object dinamis dari dict
                    symptom_obj = type('Symptom', (), {
                        'id': item.get('id'),
                        'name': item.get('name', item.get('id')),
                        'description': item.get('description', ''),
                        'species': item.get('species', [])
                    })()
                    self.symptoms[item['id']] = symptom_obj
    
    def load_diseases(self):
        """Memuat data penyakit dari diseases.json"""
        diseases_file = self.database_path / "diseases.json"
        if diseases_file.exists():
            with open(diseases_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    disease_obj = type('Disease', (), {
                        'id': item.get('id'),
                        'name': item.get('name', item.get('id')),
                        'description': item.get('description', ''),
                        'recommendation': item.get('recommendation', ''),
                        'prevention': item.get('prevention', [])
                    })()
                    self.diseases[item['id']] = disease_obj
    
    def load_rules(self):
        """Memuat rules dari rules.json"""
        rules_file = self.database_path / "rules.json"
        if rules_file.exists():
            with open(rules_file, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
    
    def get_symptom(self, symptom_id):
        """Mendapatkan gejala berdasarkan ID"""
        return self.symptoms.get(symptom_id)
    
    def get_disease(self, disease_id):
        """Mendapatkan penyakit berdasarkan ID"""
        return self.diseases.get(disease_id)
    
    def get_rule(self, rule_id):
        """Mendapatkan rule berdasarkan ID"""
        return self.rules.get(rule_id)

# Fungsi-fungsi existing untuk manajemen rules
def load_rules():
    """Memuat seluruh rules dari file JSON"""
    if not os.path.exists(RULES_PATH):
        return {}
    with open(RULES_PATH, "r") as f:
        return json.load(f)

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
