"""Inference Engine dengan komentar bahasa Indonesia.

Modul ini mengimplementasikan dua metode penalaran klasik:
- Forward chaining (data-driven): dimulai dari fakta yang diketahui dan
	menerapkan aturan untuk menurunkan fakta baru.
- Backward chaining (goal-driven): dimulai dari hipotesis/goal dan bekerja
	mundur untuk membuktikan fakta pendukung.

Format aturan (contoh):

rules = {
		'R1': {
				'IF': ['gejala_1', 'gejala_2'],  # daftar antecedent (kondisi)
				'THEN': 'diagnosa_A',            # consequent (konklusi)
				'CF': 0.8,                       # Certainty Factor aturan (opsional)
				# metadata opsional: 'ask_why', 'recommendation', 'source'
		},
}

Keluaran kedua metode adalah struktur yang ramah-frontend berisi:
- trace: langkah-langkah penalaran (baris demi baris)
- used_rules: daftar aturan yang dipakai
- reasoning_path: urutan aturan yang dipakai (string)

Catatan matematis CF yang digunakan (implementasi sederhana MYCIN-like):
- Kombinasi antecedent (konjungsi): MIN dari CF antecedent
- Aplikasi aturan: CF_baru = CF_antecedent * CF_rule
- Penggabungan bukti untuk fakta yang sama (positif):
	CF = CF_old + CF_new * (1 - CF_old)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Any


def _clamp01(x: float) -> float:
	# Pastikan nilai CF berada di rentang [0,1]
	return max(0.0, min(1.0, x))


def _combine_cf(cf_old: float, cf_new: float) -> float:
	"""Combine two positive CFs (MYCIN-style).

	Assumes both CFs are in [0, 1]. If negative CFs are needed later,
	extend with the general combination formula.
	"""
	# Gabungkan dua bukti positif: CF_total = CF_old + CF_new * (1 - CF_old)
	cf_old = _clamp01(cf_old)
	cf_new = _clamp01(cf_new)
	return _clamp01(cf_old + cf_new * (1.0 - cf_old))


def _antecedent_cf(antecedent_cfs: List[float]) -> float:
	"""Aggregate CF of antecedents using MIN (conjunctive)."""
	# Untuk aturan dengan beberapa antecedent (AND), kita ambil nilai CF terkecil
	# karena semua kondisi harus terpenuhi.
	if not antecedent_cfs:
		return 0.0
	return _clamp01(min(antecedent_cfs))


def _as_mapping(obj: Any) -> Dict[str, Any]:
	"""Best-effort to convert pydantic/dataclass/object to a plain dict."""
	if obj is None:
		return {}
	if isinstance(obj, dict):
		return obj
	# pydantic v1/2
	for attr in ("model_dump", "dict"):
		if hasattr(obj, attr):
			try:
				return getattr(obj, attr)()
			except Exception:
				pass
	# dataclass or simple object
	if hasattr(obj, "__dict__"):
		# Jika objek adalah dataclass/pydantic model, kembalikan representasi dict
		return dict(obj.__dict__)
	# Jika tidak bisa dikonversi, kembalikan dict kosong
	return {}


@dataclass
class ReasoningStep:
	step: int
	rule: str
	matched_if: List[str]
	derived: str
	cf_before: float
	delta_cf: float
	cf_after: float
	facts_before: List[str]
	facts_after: List[str]
	why: Optional[str] = None
	source: Optional[str] = None

	def to_row(self) -> Dict[str, Any]:
		return {
			"step": self.step,
			"rule": self.rule,
			"matched_if": ", ".join(self.matched_if),
			"derived": self.derived,
			"cf_before": round(self.cf_before, 3),
			"delta_cf": round(self.delta_cf, 3),
			"cf_after": round(self.cf_after, 3),
			"facts_before": ", ".join(self.facts_before),
			"facts_after": ", ".join(self.facts_after),
			"why": self.why,
			"source": self.source,
		}




class InferenceEngine:
	"""Expert system inference engine.

	Provides:
	- Forward chaining (data-driven)
	- Backward chaining (goal-driven)
	- Certainty Factor (CF) support
	- Frontend-friendly results: step-by-step trace, used rules, reasoning path
	"""

	def __init__(self, threshold: float = 0.6):
		self.threshold = threshold

	# ----------------------------- Public API ----------------------------- #
	def forward_chaining(
		self,
		rules: Dict[str, Dict[str, Any]],
		initial_facts_cf: Dict[str, float],
		limit: int | None = None,
	) -> Dict[str, Any]:
		"""Run forward chaining.

		Args:
			rules: mapping rule_id -> {IF: [...], THEN: str, CF?: float, ...}
			initial_facts_cf: mapping fact -> CF in [0,1]
			limit: optional max number of fired rules

		Returns:
			dict with keys:
			- method: "forward"
			- facts_cf: {fact: cf}
			- conclusions: {fact: cf}  (includes any derived facts)
			- used_rules: [rule_id, ...]
			- reasoning_path: "R1 -> R3 -> ..."
			- trace: [rows...]
		"""
		# Inisialisasi fakta dari input dan siapkan struktur pelacakan
		facts_cf: Dict[str, float] = {k: _clamp01(v) for k, v in (initial_facts_cf or {}).items()}
		facts: Set[str] = set(facts_cf)
		used_rules: List[str] = []
		steps: List[ReasoningStep] = []

		# Loop sampai tidak ada aturan yang bisa ditembakkan atau mencapai batas
		fired = True
		step_no = 0
		max_steps = limit if limit is not None else max(50, len(rules) * 3)

		while fired and step_no < max_steps:
			fired = False
			for rid, r in rules.items():
				# Jika antecedent aturan belum semua muncul pada fakta, skip
				antecedents: List[str] = list(r.get("IF", []))
				if not antecedents:
					continue
				if not set(antecedents).issubset(facts):
					continue  # belum terpenuhi semua kondisi

				# Hitung CF gabungan dari antecedent (MIN karena AND)
				ant_cfs = [facts_cf.get(a, 0.0) for a in antecedents]
				ant_cf = _antecedent_cf(ant_cfs)
				rule_cf = float(r.get("CF", 1.0))
				proposed_cf = _clamp01(ant_cf * rule_cf)

				then_fact = r.get("THEN")
				if not then_fact:
					continue

				# Gabungkan dengan CF yang sudah ada untuk fakta tujuan
				before_cf = facts_cf.get(then_fact, 0.0)
				after_cf = _combine_cf(before_cf, proposed_cf)
				delta = after_cf - before_cf
				# Jika tidak ada peningkatan signifikan, jangan simpan langkah
				if delta <= 1e-6:
					continue

				# Tembakkan aturan: simpan perubahan dan catat langkah
				fired = True
				step_no += 1
				used_rules.append(rid)
				facts.add(then_fact)
				facts_cf[then_fact] = after_cf

				# Simpan rincian langkah untuk trace (ditampilkan pada UI)
				step = ReasoningStep(
					step=step_no,
					rule=rid,
					matched_if=antecedents,
					derived=str(then_fact),
					cf_before=before_cf,
					delta_cf=delta,
					cf_after=after_cf,
					facts_before=sorted(list(facts - {then_fact})),
					facts_after=sorted(list(facts)),
					why=r.get("ask_why"),
					source=r.get("source"),
				)
				steps.append(step)

			# akhir iterasi aturan

		# Kembalikan hasil lengkap termasuk trace yang mudah dikirim ke frontend
		return {
			"method": "forward",
			"facts_cf": facts_cf,
			"conclusions": {k: v for k, v in facts_cf.items()},
			"used_rules": used_rules,
			"reasoning_path": " -> ".join(used_rules),
			"trace": [s.to_row() for s in steps],
		}

	def backward_chaining(
		self,
		rules: Dict[str, Dict[str, Any]],
		facts_cf: Dict[str, float],
		goal: str,
		_visited: Optional[Set[str]] = None,
	) -> Dict[str, Any]:
		"""Attempt to prove goal using backward chaining.

		Returns dict:
			- method: "backward"
			- success: bool
			- goal: str
			- cf: float
			- used_rules: list[str]
			- reasoning_path: "R5 -> R2 -> ..."
			- trace: list[rows]
		"""
		# visited: set untuk menghindari loop rekursif yang tak berujung
		visited = set(_visited or set())

		# Jika goal sudah ada sebagai fakta dengan CF > 0, langsung berhasil
		if goal in facts_cf and facts_cf[goal] > 0.0:
			return {
				"method": "backward",
				"success": True,
				"goal": goal,
				"cf": _clamp01(facts_cf[goal]),
				"used_rules": [],
				"reasoning_path": "",
				"trace": [],
			}

		# Pilih aturan yang menghasilkan goal (THEN == goal)
		candidate_rules = [(rid, r) for rid, r in rules.items() if r.get("THEN") == goal]
		best_result: Dict[str, Any] = {
			"method": "backward",
			"success": False,
			"goal": goal,
			"cf": 0.0,
			"used_rules": [],
			"reasoning_path": "",
			"trace": [],
		}

		# Jika sudah dikunjungi, hentikan agar tidak terjadi siklus tak hingga
		if goal in visited:
			return best_result
		visited.add(goal)

		# Coba setiap aturan kandidat: buktikan semua antecedent secara rekursif
		for rid, rule in candidate_rules:
			antecedents: List[str] = list(rule.get("IF", []))
			local_used: List[str] = []
			local_trace: List[Dict[str, Any]] = []
			ant_cfs: List[float] = []
			ok = True

			# Untuk tiap antecedent, jika sudah fakta pakai langsung, jika tidak coba buktikan
			for a in antecedents:
				if a in facts_cf and facts_cf[a] > 0.0:
					ant_cfs.append(facts_cf[a])
					continue
				# Buktikan sub-goal secara rekursif
				sub = self.backward_chaining(rules, facts_cf, a, visited)
				if not sub.get("success"):
					ok = False
					break
				# Jika subgoal terbukti, gunakan CF hasilnya
				ant_cfs.append(float(sub.get("cf", 0.0)))
				local_used += sub.get("used_rules", [])
				local_trace += sub.get("trace", [])

			if not ok:
				# Jika salah satu antecedent gagal dibuktikan, aturan ini tidak bisa dipakai
				continue

			# Hitung CF untuk goal berdasarkan antecedent yang terbukti
			ant_cf = _antecedent_cf(ant_cfs)
			rule_cf = float(rule.get("CF", 1.0))
			goal_cf = _clamp01(ant_cf * rule_cf)

			# Pilih hasil terbaik (CF tertinggi) jika ada beberapa bukti
			if goal_cf > best_result["cf"]:
				step = ReasoningStep(
					step=len(local_trace) + 1,
					rule=rid,
					matched_if=antecedents,
					derived=goal,
					cf_before=0.0,
					delta_cf=goal_cf,
					cf_after=goal_cf,
					facts_before=sorted(list(facts_cf.keys())),
					facts_after=sorted(list(set(list(facts_cf.keys()) + [goal]))),
					why=rule.get("ask_why"),
					source=rule.get("source"),
				)
				best_result = {
					"method": "backward",
					"success": True,
					"goal": goal,
					"cf": goal_cf,
					"used_rules": local_used + [rid],
					"reasoning_path": " -> ".join(local_used + [rid]),
					"trace": local_trace + [step.to_row()],
				}

		return best_result

	def diagnose(
		self,
		symptom_ids: List[str],
		user_cf: float,
		kb: Any,
	) -> Dict[str, Any]:
		"""High-level diagnosis pipeline used by the UI.

		- Builds initial facts with user CF and symptom weights (if provided)
		- Runs forward chaining to derive candidate diseases/derived facts
		- Selects the best disease above threshold
		- Returns a payload tailored for frontend consumption
		"""
		# Siapkan basis aturan dan fakta awal
		rules = {rid: _as_mapping(r) for rid, r in getattr(kb, "rules", {}).items()}

		# Bangun fakta awal berdasarkan gejala dan bobot gejala di KB
		initial_facts_cf: Dict[str, float] = {}
		user_cf = _clamp01(user_cf or 1.0)

		symptoms_map = getattr(kb, "symptoms", {})
		for sid in symptom_ids:
			s_obj = symptoms_map.get(sid)
			s_map = _as_mapping(s_obj)
			weight = float(s_map.get("weight", 1.0))
			# Fakta awal CF = input user * bobot gejala
			initial_facts_cf[sid] = _clamp01(user_cf * weight)

		# Jalankan forward chaining untuk menurunkan kesimpulan
		fwd = self.forward_chaining(rules, initial_facts_cf)

		# Pilih penyakit terbaik (jika ada) dari daftar disease di KB
		diseases: Dict[str, Any] = getattr(kb, "diseases", {})
		best_id: Optional[str] = None
		best_cf = 0.0
		for did in diseases.keys() or []:
			cf = float(fwd["conclusions"].get(did, 0.0))
			if cf > best_cf:
				best_cf = cf
				best_id = did

		# Siapkan payload hasil yang akan dikirim ke frontend
		trace_rows = fwd.get("trace", [])
		used_rules = fwd.get("used_rules", [])
		reasoning_path = fwd.get("reasoning_path", "")

		result: Dict[str, Any] = {
			"method": "forward",
			"facts": list(initial_facts_cf.keys()),
			"trace": trace_rows,
			"used_rules": used_rules,
			"reasoning_path": reasoning_path,
		}

		# Jika ada konklusi dengan CF di atas threshold, tambahkan informasi lengkap
		if best_id and best_cf >= self.threshold:
			disease_obj = diseases.get(best_id)
			d_map = _as_mapping(disease_obj)
			# Cari rekomendasi dari rule terakhir yang menghasilkan penyakit ini
			recommendation: Optional[str] = None
			for rid in reversed(used_rules):
				rmap = rules.get(rid, {})
				if rmap.get("THEN") == best_id:
					recommendation = rmap.get("recommendation") or None
					if recommendation:
						break
			# Jika tidak ada rekomendasi rule, gunakan pengobatan pertama dari disease
			if not recommendation:
				treatments = d_map.get("treatments") or []
				if isinstance(treatments, list) and treatments:
					recommendation = treatments[0]

			result.update({
				"conclusion": best_id,
				"conclusion_label": d_map.get("name", best_id),
				"cf": round(best_cf, 3),
				"recommendation": recommendation,
				"prevention": d_map.get("prevention", []) or [],
			})
		else:
			# Jika tidak ada kesimpulan kuat, tetap kembalikan trace untuk transparansi
			result.update({
				"conclusion": None,
				"cf": 0.0,
			})

		return result


# Optional: simple manual check when running this module directly
if __name__ == "__main__":
	kb_rules = {
		'R1': {'IF': ['gejala_1', 'gejala_2'], 'THEN': 'diagnosa_A', 'CF': 0.8},
		'R2': {'IF': ['gejala_3', 'diagnosa_A'], 'THEN': 'diagnosa_B', 'CF': 0.7},
	}
	engine = InferenceEngine(threshold=0.5)
	res = engine.forward_chaining(kb_rules, {"gejala_1": 1.0, "gejala_2": 0.9, "gejala_3": 0.8})
	print("Forward chaining:", res["conclusions"])  # quick sanity

