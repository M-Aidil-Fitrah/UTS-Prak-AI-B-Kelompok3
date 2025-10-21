import json
import os

RULES_PATH = "database/rules.json"

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
    print(f"✅ Rule {rule_id} berhasil ditambahkan.")

def edit_rule(rule_id, symptoms=None, disease_id=None, cf=None):
    """Mengedit rule yang sudah ada"""
    rules = load_rules()
    if rule_id not in rules:
        print(f"❌ Rule {rule_id} tidak ditemukan.")
        return
    if symptoms:
        rules[rule_id]["IF"] = symptoms
    if disease_id:
        rules[rule_id]["THEN"] = disease_id
    if cf is not None:
        rules[rule_id]["CF"] = cf
    save_rules(rules)
    print(f"✏️ Rule {rule_id} berhasil diperbarui.")

def delete_rule(rule_id):
    """Menghapus rule dari file"""
    rules = load_rules()
    if rule_id in rules:
        del rules[rule_id]
        save_rules(rules)
        print(f"🗑️ Rule {rule_id} berhasil dihapus.")
    else:
        print(f"❌ Rule {rule_id} tidak ditemukan.")

if __name__ == "__main__":
    # Contoh penggunaan
    add_rule("R4", ["G6", "G8"], "P2", 0.75)
