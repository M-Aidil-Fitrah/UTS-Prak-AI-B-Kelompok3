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


def _matches_text(item: Dict[str, Any], query: str, fields: List[str]) -> bool:
	"""Cek apakah item cocok dengan query pada field-field tertentu.
	
	Args:
		item: dictionary yang berisi data (gejala/penyakit/rule)
		query: kata kunci pencarian
		fields: daftar nama field yang akan dicari (mis: ['name', 'description', 'id'])
	
	Returns:
		True jika query ditemukan di salah satu field
	"""
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


def search_symptoms(
	symptoms: Dict[str, Any],
	query: Optional[str] = None,
	species_filter: Optional[List[str]] = None,
	weight_min: Optional[float] = None,
	weight_max: Optional[float] = None,
	sort_by: str = "id",
	ascending: bool = True
) -> List[Dict[str, Any]]:
	"""Cari dan filter gejala berdasarkan berbagai kriteria.
	
	Args:
		symptoms: dictionary {symptom_id: symptom_object}
		query: kata kunci untuk mencari di nama, deskripsi, atau ID
		species_filter: list spesies (mis. ["Lele", "Nila"]) - hanya gejala yang terkait
		weight_min: bobot minimum (CF weight)
		weight_max: bobot maksimum
		sort_by: field untuk sorting ('id', 'name', 'weight')
		ascending: True untuk ascending, False untuk descending
	
	Returns:
		List dictionary hasil filter dan sort
	"""
	results = []
	
	for sid, s_obj in symptoms.items():
		# Konversi object ke dict jika perlu
		if hasattr(s_obj, "model_dump"):
			s = s_obj.model_dump()
		elif hasattr(s_obj, "__dict__"):
			s = dict(s_obj.__dict__)
		else:
			s = dict(s_obj) if isinstance(s_obj, dict) else {"id": sid}
		
		# Pastikan ID ada
		if "id" not in s:
			s["id"] = sid
		
		# Filter berdasarkan query teks
		if query and not _matches_text(s, query, ["id", "name", "nama", "description", "deskripsi"]):
			continue
		
		# Filter berdasarkan spesies
		if species_filter:
			symptom_species = s.get("species", [])
			if isinstance(symptom_species, str):
				symptom_species = [symptom_species]
			# Jika symptom tidak punya species (None/empty), lewati filter ini
			# Jika punya species, cek apakah ada yang cocok dengan filter
			if symptom_species and not any(sp in species_filter for sp in symptom_species):
				continue
		
		# Filter berdasarkan weight/bobot
		weight = float(s.get("weight", 1.0))
		if weight_min is not None and weight < weight_min:
			continue
		if weight_max is not None and weight > weight_max:
			continue
		
		results.append(s)
	
	# Sorting
	if sort_by in ["name", "nama"]:
		key_fn = lambda x: _normalize_text(x.get("name") or x.get("nama") or x.get("id", ""))
	elif sort_by == "weight":
		key_fn = lambda x: float(x.get("weight", 1.0))
	else:  # default: sort by id
		key_fn = lambda x: x.get("id", "")
	
	results.sort(key=key_fn, reverse=not ascending)
	return results


def search_diseases(
	diseases: Dict[str, Any],
	query: Optional[str] = None,
	species_filter: Optional[List[str]] = None,
	sort_by: str = "id",
	ascending: bool = True
) -> List[Dict[str, Any]]:
	"""Cari dan filter penyakit berdasarkan berbagai kriteria.
	
	Args:
		diseases: dictionary {disease_id: disease_object}
		query: kata kunci untuk mencari di nama, deskripsi, penyebab, pengobatan, dll
		species_filter: list spesies (jika disease punya field species)
		sort_by: field untuk sorting ('id', 'name', 'nama')
		ascending: True untuk ascending, False untuk descending
	
	Returns:
		List dictionary hasil filter dan sort
	"""
	results = []
	
	for did, d_obj in diseases.items():
		# Konversi object ke dict
		if hasattr(d_obj, "model_dump"):
			d = d_obj.model_dump()
		elif hasattr(d_obj, "__dict__"):
			d = dict(d_obj.__dict__)
		else:
			d = dict(d_obj) if isinstance(d_obj, dict) else {"id": did}
		
		if "id" not in d:
			d["id"] = did
		
		# Filter berdasarkan query teks (cari di banyak field)
		search_fields = [
			"id", "name", "nama", "description", "deskripsi",
			"penyebab", "pengobatan", "pencegahan", "treatments", "prevention"
		]
		if query and not _matches_text(d, query, search_fields):
			continue
		
		# Filter berdasarkan spesies (jika ada)
		if species_filter:
			disease_species = d.get("species", [])
			if isinstance(disease_species, str):
				disease_species = [disease_species]
			if disease_species and not any(sp in species_filter for sp in disease_species):
				continue
		
		results.append(d)
	
	# Sorting
	if sort_by in ["name", "nama"]:
		key_fn = lambda x: _normalize_text(x.get("name") or x.get("nama") or x.get("id", ""))
	else:
		key_fn = lambda x: x.get("id", "")
	
	results.sort(key=key_fn, reverse=not ascending)
	return results


def search_rules(
	rules: Dict[str, Dict[str, Any]],
	query: Optional[str] = None,
	antecedent_filter: Optional[str] = None,
	consequent_filter: Optional[str] = None,
	cf_min: Optional[float] = None,
	cf_max: Optional[float] = None,
	sort_by: str = "id",
	ascending: bool = True
) -> List[Dict[str, Any]]:
	"""Cari dan filter rules berdasarkan berbagai kriteria.
	
	Args:
		rules: dictionary {rule_id: rule_dict}
		query: kata kunci untuk mencari di ID, why, recommendation, source
		antecedent_filter: hanya rules yang memiliki antecedent ini (mis. "bintik_putih")
		consequent_filter: hanya rules yang menghasilkan consequent ini (mis. "P1")
		cf_min: CF minimum
		cf_max: CF maksimum
		sort_by: field untuk sorting ('id', 'cf')
		ascending: True untuk ascending, False untuk descending
	
	Returns:
		List dictionary hasil filter dan sort (setiap dict punya key 'id' dan field rule)
	"""
	results = []
	
	for rid, r in rules.items():
		# Konversi object ke dict jika perlu
		if hasattr(r, "model_dump"):
			rule_data = r.model_dump()
		elif hasattr(r, "__dict__"):
			rule_data = dict(r.__dict__)
		else:
			rule_data = dict(r) if isinstance(r, dict) else {}
		
		# Tambahkan ID rule jika belum ada
		rule_with_id = {"id": rid, **rule_data}
		
		# Filter berdasarkan query teks
		if query:
			search_fields = ["id", "ask_why", "recommendation", "source", "THEN"]
			# Tambahkan antecedent ke pencarian (IF adalah list)
			if_list = rule_data.get("IF", [])
			rule_with_id["_if_text"] = " ".join(if_list)  # bantu field untuk search
			search_fields.append("_if_text")
			
			if not _matches_text(rule_with_id, query, search_fields):
				continue
		
		# Filter berdasarkan antecedent (IF mengandung item tertentu)
		if antecedent_filter:
			antecedents = rule_data.get("IF", [])
			if antecedent_filter not in antecedents:
				continue
		
		# Filter berdasarkan consequent (THEN)
		if consequent_filter:
			consequent = rule_data.get("THEN", "")
			if consequent != consequent_filter:
				continue
		
		# Filter berdasarkan CF range
		cf = float(rule_data.get("CF", 1.0))
		if cf_min is not None and cf < cf_min:
			continue
		if cf_max is not None and cf > cf_max:
			continue
		
		results.append(rule_with_id)
	
	# Sorting
	if sort_by == "cf":
		key_fn = lambda x: float(x.get("CF", 1.0))
	else:
		key_fn = lambda x: x.get("id", "")
	
	results.sort(key=key_fn, reverse=not ascending)
	return results


def filter_by_species(
	items: List[Dict[str, Any]],
	species_list: List[str]
) -> List[Dict[str, Any]]:
	"""Filter generik berdasarkan spesies.
	
	Helper function untuk memfilter list item (gejala/penyakit) berdasarkan spesies.
	Item yang tidak punya field 'species' akan tetap disertakan (dianggap umum).
	
	Args:
		items: list dictionary yang mungkin punya field 'species'
		species_list: list spesies yang ingin difilter (mis. ["Lele", "Nila"])
	
	Returns:
		List item yang cocok dengan filter atau tidak punya species (umum)
	"""
	if not species_list:
		return items
	
	filtered = []
	for item in items:
		item_species = item.get("species", [])
		if isinstance(item_species, str):
			item_species = [item_species]
		
		# Jika item tidak punya species, dianggap umum untuk semua spesies
		if not item_species:
			filtered.append(item)
			continue
		
		# Jika ada species yang cocok dengan filter, masukkan
		if any(sp in species_list for sp in item_species):
			filtered.append(item)
	
	return filtered


def get_rules_by_disease(
	rules: Dict[str, Dict[str, Any]],
	disease_id: str
) -> List[Dict[str, Any]]:
	"""Dapatkan semua rules yang menghasilkan penyakit tertentu.
	
	Args:
		rules: dictionary rules
		disease_id: ID penyakit yang dicari
	
	Returns:
		List rules yang THEN-nya adalah disease_id tersebut
	"""
	return search_rules(rules, consequent_filter=disease_id)


def get_rules_by_symptom(
	rules: Dict[str, Dict[str, Any]],
	symptom_id: str
) -> List[Dict[str, Any]]:
	"""Dapatkan semua rules yang menggunakan gejala tertentu.
	
	Args:
		rules: dictionary rules
		symptom_id: ID gejala yang dicari
	
	Returns:
		List rules yang IF-nya mengandung symptom_id tersebut
	"""
	return search_rules(rules, antecedent_filter=symptom_id)


def get_related_symptoms(
	rules: Dict[str, Dict[str, Any]],
	symptom_id: str
) -> List[str]:
	"""Dapatkan gejala-gejala lain yang sering muncul bersama gejala tertentu.
	
	Berguna untuk rekomendasi "gejala terkait" di UI.
	
	Args:
		rules: dictionary rules
		symptom_id: ID gejala yang dicari
	
	Returns:
		List ID gejala lain yang muncul dalam rules yang sama
	"""
	related = set()
	for rid, r in rules.items():
		antecedents = r.get("IF", [])
		if symptom_id in antecedents:
			# Tambahkan gejala lain dari rule ini
			for ant in antecedents:
				if ant != symptom_id:
					related.add(ant)
	return sorted(list(related))


def get_possible_diseases(
	rules: Dict[str, Dict[str, Any]],
	symptom_ids: List[str]
) -> List[str]:
	"""Dapatkan daftar penyakit yang mungkin berdasarkan gejala yang dipilih.
	
	Berguna untuk preview atau hints sebelum menjalankan inferensi penuh.
	
	Args:
		rules: dictionary rules
		symptom_ids: list ID gejala yang sudah dipilih user
	
	Returns:
		List ID penyakit yang mungkin (consequent dari rules yang antecedent-nya cocok)
	"""
	possible = set()
	symptom_set = set(symptom_ids)
	
	for rid, r in rules.items():
		antecedents = set(r.get("IF", []))
		# Jika ada intersection (sebagian antecedent terpenuhi), tambahkan consequent
		if antecedents & symptom_set:  # ada irisan
			consequent = r.get("THEN")
			if consequent:
				possible.add(consequent)
	
	return sorted(list(possible))


def highlight_search_term(text: str, query: str) -> str:
	"""Highlight query di dalam text untuk tampilan UI (gunakan markdown bold).
	
	Args:
		text: teks asli
		query: kata kunci yang ingin di-highlight
	
	Returns:
		Text dengan query yang di-bold menggunakan markdown **...**
	"""
	if not query or not text:
		return text
	
	# Case-insensitive replace dengan bold markdown
	pattern = re.compile(re.escape(query), re.IGNORECASE)
	return pattern.sub(lambda m: f"**{m.group(0)}**", text)


# ===== Contoh penggunaan (untuk testing) =====
if __name__ == "__main__":
	# Contoh data dummy
	dummy_symptoms = {
		"G1": {"id": "G1", "name": "Bintik Putih", "description": "Bintik putih di tubuh", "weight": 1.0, "species": ["Lele", "Nila"]},
		"G2": {"id": "G2", "name": "Nafsu Makan Turun", "description": "Ikan tidak mau makan", "weight": 0.9, "species": []},
		"G3": {"id": "G3", "name": "Insang Pucat", "description": "Warna insang tidak normal", "weight": 0.95, "species": ["Nila", "Gurame"]},
	}
	
	dummy_rules = {
		"R1": {"IF": ["G1", "G2"], "THEN": "P1", "CF": 0.8, "ask_why": "Bintik putih khas Ich"},
		"R2": {"IF": ["G2", "G3"], "THEN": "P2", "CF": 0.7},
		"R3": {"IF": ["G1"], "THEN": "P1", "CF": 0.6},
	}
	
	# Test search symptoms
	print("=== Test Search Symptoms ===")
	hasil = search_symptoms(dummy_symptoms, query="putih", species_filter=["Lele"])
	print(f"Hasil pencarian 'putih' untuk Lele: {len(hasil)} item")
	for h in hasil:
		print(f"  - {h['id']}: {h['name']}")
	
	# Test search rules by symptom
	print("\n=== Test Get Rules by Symptom ===")
	rules_g1 = get_rules_by_symptom(dummy_rules, "G1")
	print(f"Rules yang menggunakan G1: {len(rules_g1)} rules")
	for r in rules_g1:
		print(f"  - {r['id']}: IF {r['IF']} THEN {r['THEN']}")
	
	# Test get possible diseases
	print("\n=== Test Get Possible Diseases ===")
	diseases = get_possible_diseases(dummy_rules, ["G1", "G2"])
	print(f"Penyakit yang mungkin dari G1+G2: {diseases}")
	
	print("\n✅ Semua test search_filter.py berjalan sukses!")
