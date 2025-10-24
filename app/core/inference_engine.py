"""Inference Engine.

Modul ini mengkoordinasikan komponen-komponen:
- WorkingMemory: Kelola fakta dan CF
- ExplanationFacility: Generate penjelasan WHY/HOW
- InferenceEngine: Orchestrator untuk forward/backward chaining
- Integrasi dengan database_manager untuk akses rules, symptoms, diseases
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import sys
import os

# Import dari modul baru
from .working_memory import WorkingMemory
from .explanation import ExplanationFacility, ReasoningStep

# Import database functions untuk integrasi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from database.database_manager import load_rules
except ImportError:
    # Fallback jika path tidak bekerja
    from ..database.database_manager import load_rules


class InferenceEngine:
    """Expert system inference engine (Refactored).
    
    Sekarang lebih modular dengan:
    - WorkingMemory untuk kelola fakta
    - ExplanationFacility untuk penjelasan
    - Fokus pada algoritma inferensi
    """

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.working_memory: Optional[WorkingMemory] = None
        self.explanation: Optional[ExplanationFacility] = None

    def forward_chaining(
        self,
        rules: Dict[str, Dict[str, Any]],
        initial_facts_cf: Dict[str, float],
        kb: Any = None,  # Untuk explanation
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """Run forward chaining (DISEDERHANAKAN).
        
        Logika utama dipindah ke helper methods.
        Working memory dan explanation dikelola terpisah.
        """
        # Initialize components
        self.working_memory = WorkingMemory()
        self.working_memory.add_initial_facts(initial_facts_cf)
        
        if kb:
            self.explanation = ExplanationFacility(rules, kb)
        
        # Run inference loop
        used_rules = self._inference_loop(rules, limit)
        
        # Build result
        return {
            "method": "forward",
            "facts_cf": self.working_memory.facts_cf,
            "conclusions": self.working_memory.facts_cf.copy(),
            "used_rules": used_rules,
            "reasoning_path": " -> ".join(used_rules),
            "trace": self.explanation.get_trace_formatted() if self.explanation else [],
        }
    
    def _inference_loop(
        self, 
        rules: Dict[str, Dict[str, Any]], 
        limit: Optional[int]
    ) -> List[str]:
        """Loop inferensi (REWRITTEN).
        
        Logika ini ditulis ulang sepenuhnya untuk memastikan setiap aturan hanya
        dieksekusi MAKSIMAL SATU KALI, mencegah loop tak terbatas dan jejak
        penalaran yang berulang.
        """
        used_rules_in_trace = []
        fired_rules_ever = set()  # Set untuk melacak semua aturan yang pernah dieksekusi.
        
        while True: # Loop akan berhenti secara internal.
            newly_fired_rules_this_pass = []
            
            # Iterasi hanya pada aturan yang BELUM PERNAH dieksekusi.
            for rid, rule in rules.items():
                if rid in fired_rules_ever:
                    continue
                
                # Jika aturan bisa dieksekusi, tembak dan catat.
                if self._can_fire_rule(rule):
                    step_no = len(used_rules_in_trace) + 1
                    fired_data = self._fire_rule(rid, rule, step_no)
                    
                    if fired_data:
                        newly_fired_rules_this_pass.append(rid)
            
            # Jika tidak ada aturan baru yang dieksekusi dalam satu putaran penuh,
            # berarti proses inferensi selesai.
            if not newly_fired_rules_this_pass:
                break # Keluar dari loop while True.
            
            # Tambahkan aturan yang baru dieksekusi ke catatan utama.
            for rid in newly_fired_rules_this_pass:
                used_rules_in_trace.append(rid)
                fired_rules_ever.add(rid)
                
            # Pengaman jika terjadi loop yang tidak terduga.
            if len(used_rules_in_trace) >= (limit or 100):
                break
                
        return used_rules_in_trace
    
    def _can_fire_rule(self, rule: Dict[str, Any]) -> bool:
        """Check apakah rule bisa ditembakkan."""
        antecedents = rule.get("IF", [])
        if not antecedents:
            return False
        return self.working_memory.has_all_facts(antecedents)
    
    def _fire_rule(
        self, 
        rule_id: str, 
        rule: Dict[str, Any], 
        step_no: int
    ) -> Optional[Dict[str, Any]]:
        """Tembakkan rule dan update working memory.
        
        Returns None jika tidak ada perubahan signifikan.
        """
        antecedents = rule.get("IF", [])
        then_fact = rule.get("THEN")
        
        if not then_fact:
            return None
        
        # Calculate CF
        ant_cfs = [
            self.working_memory.get_fact(a) or 0.0 
            for a in antecedents
        ]
        ant_cf = min(ant_cfs) if ant_cfs else 0.0
        rule_cf = float(rule.get("CF", 1.0))
        proposed_cf = min(1.0, ant_cf * rule_cf)
        
        # Update working memory
        before_cf = self.working_memory.get_fact(then_fact) or 0.0
        delta = self.working_memory.add_fact(
            then_fact, 
            proposed_cf, 
            source=f"rule_{rule_id}",
            derived_from=antecedents
        )
        
        if delta <= 1e-6:
            return None  # No significant change
        
        after_cf = self.working_memory.get_fact(then_fact)
        
        # Add to explanation trace
        if self.explanation:
            step = ReasoningStep(
                step=step_no,
                rule=rule_id,
                matched_if=antecedents,
                derived=then_fact,
                cf_before=before_cf,
                delta_cf=delta,
                cf_after=after_cf,
                facts_before=sorted(list(self.working_memory.get_facts_set() - {then_fact})),
                facts_after=sorted(list(self.working_memory.get_facts_set())),
                why=rule.get("ask_why"),
                source=rule.get("source"),
            )
            self.explanation.add_trace_step(step)
        
        return {"delta": delta, "cf": after_cf}
    
    def backward_chaining(
        self,
        rules: Dict[str, Dict[str, Any]],
        facts_cf: Dict[str, float],
        goal: str,
        kb: Any = None,
        _visited: Optional[set] = None,
    ) -> Dict[str, Any]:
        """Run backward chaining (goal-driven reasoning).
        
        Args:
            rules: mapping rule_id -> {IF: [...], THEN: str, CF?: float, ...}
            facts_cf: mapping fact -> CF in [0,1]
            goal: goal fact to prove
            kb: knowledge base untuk explanation (optional)
            _visited: internal set untuk mencegah infinite recursion
        
        Returns:
            dict with keys:
            - method: "backward"
            - success: bool
            - goal: str
            - cf: float
            - used_rules: [rule_id, ...]
            - reasoning_path: "R5 -> R2 -> ..."
            - trace: [rows...]
        """
        # Initialize visited set
        visited = set(_visited or set())
        
        # Base case: jika goal sudah ada sebagai fakta dengan CF > 0
        if goal in facts_cf and facts_cf[goal] > 0.0:
            return {
                "method": "backward",
                "success": True,
                "goal": goal,
                "cf": min(1.0, max(0.0, facts_cf[goal])),
                "used_rules": [],
                "reasoning_path": "",
                "trace": [],
            }
        
        # Cegah infinite loop
        if goal in visited:
            return {
                "method": "backward",
                "success": False,
                "goal": goal,
                "cf": 0.0,
                "used_rules": [],
                "reasoning_path": "",
                "trace": [],
            }
        
        visited.add(goal)
        
        # Initialize explanation jika ada KB
        if kb and not self.explanation:
            self.explanation = ExplanationFacility(rules, kb)
        
        # Cari rules yang bisa menghasilkan goal (THEN == goal)
        candidate_rules = [
            (rid, rule) 
            for rid, rule in rules.items() 
            if rule.get("THEN") == goal
        ]
        
        if not candidate_rules:
            # Tidak ada rule yang menghasilkan goal
            return {
                "method": "backward",
                "success": False,
                "goal": goal,
                "cf": 0.0,
                "used_rules": [],
                "reasoning_path": "",
                "trace": [],
            }
        
        # Coba setiap candidate rule
        best_result = None
        best_cf = 0.0
        
        for rule_id, rule in candidate_rules:
            antecedents = rule.get("IF", [])
            if not antecedents:
                continue
            
            # Buktikan semua antecedent secara rekursif
            ant_cfs = []
            sub_used_rules = []
            sub_traces = []
            all_proved = True
            
            for antecedent in antecedents:
                # Jika antecedent sudah ada sebagai fakta, gunakan langsung
                if antecedent in facts_cf and facts_cf[antecedent] > 0.0:
                    ant_cfs.append(facts_cf[antecedent])
                else:
                    # Coba buktikan antecedent sebagai sub-goal
                    sub_result = self.backward_chaining(
                        rules, 
                        facts_cf, 
                        antecedent, 
                        kb,
                        visited.copy()
                    )
                    
                    if sub_result["success"]:
                        ant_cfs.append(sub_result["cf"])
                        sub_used_rules.extend(sub_result["used_rules"])
                        sub_traces.extend(sub_result["trace"])
                    else:
                        all_proved = False
                        break
            
            if not all_proved:
                continue
            
            # Hitung CF untuk goal
            ant_cf = min(ant_cfs) if ant_cfs else 0.0
            rule_cf = float(rule.get("CF", 1.0))
            goal_cf = min(1.0, max(0.0, ant_cf * rule_cf))
            
            # Update best result jika CF lebih tinggi
            if goal_cf > best_cf:
                best_cf = goal_cf
                
                # Create trace step
                trace_step = ReasoningStep(
                    step=len(sub_traces) + 1,
                    rule=rule_id,
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
                
                all_traces = sub_traces + [trace_step.to_row()]
                all_used_rules = sub_used_rules + [rule_id]
                
                best_result = {
                    "method": "backward",
                    "success": True,
                    "goal": goal,
                    "cf": goal_cf,
                    "used_rules": all_used_rules,
                    "reasoning_path": " -> ".join(all_used_rules),
                    "trace": all_traces,
                }
        
        if best_result:
            return best_result
        else:
            return {
                "method": "backward",
                "success": False,
                "goal": goal,
                "cf": 0.0,
                "used_rules": [],
                "reasoning_path": "",
                "trace": [],
            }
    
    def diagnose(
        self,
        symptom_ids: List[str],
        user_cf: float,
        kb: Any,
    ) -> Dict[str, Any]:
        """High-level diagnosis pipeline for frontend.
        
        Builds initial facts from symptoms, runs forward chaining,
        selects best disease above threshold, and returns complete result.
        """
        # Helper function untuk konversi object ke dict
        def _as_mapping(obj: Any) -> Dict[str, Any]:
            if obj is None: return {}
            if isinstance(obj, dict): return obj
            for attr in ("model_dump", "dict"):
                if hasattr(obj, attr):
                    try: return getattr(obj, attr)()
                    except Exception: pass
            if hasattr(obj, "__dict__"): return dict(obj.__dict__)
            return {}
        
        # Convert rules ke dict format
        rules = {rid: _as_mapping(r) for rid, r in getattr(kb, "rules", {}).items()}
        
        # Build initial facts
        initial_facts_cf: Dict[str, float] = {}
        user_cf_clamped = min(1.0, max(0.0, user_cf or 1.0))
        symptoms_map = getattr(kb, "symptoms", {})
        for sid in symptom_ids:
            s_map = _as_mapping(symptoms_map.get(sid))
            weight = float(s_map.get("weight", 1.0))
            initial_facts_cf[sid] = min(1.0, max(0.0, user_cf_clamped * weight))
        
        # Run forward chaining
        fwd_result = self.forward_chaining(rules, initial_facts_cf, kb)
        
        # Cari disease terbaik dari conclusions
        diseases = getattr(kb, "diseases", {})
        best_disease_id: Optional[str] = None
        best_cf = 0.0
        for disease_id in diseases.keys():
            cf = float(fwd_result["conclusions"].get(disease_id, 0.0))
            if cf > best_cf:
                best_cf = cf
                best_disease_id = disease_id
        
        # Siapkan data untuk frontend menggunakan ExplanationFacility
        symptom_details = self.explanation.get_symptom_details(symptom_ids) if self.explanation else []
        used_rules = fwd_result.get("used_rules", [])
        rules_details = self.explanation.get_rules_details(used_rules) if self.explanation and used_rules else []

        result: Dict[str, Any] = {
            "method": "forward",
            "facts": list(initial_facts_cf.keys()),
            "trace": fwd_result.get("trace", []),
            "used_rules": used_rules,
            "reasoning_path": fwd_result.get("reasoning_path", ""),
            "symptom_details": symptom_details,
            "rules_details": rules_details,
        }
        
        # Jika ada conclusion di atas threshold
        if best_disease_id and best_cf >= self.threshold:
            disease_obj = diseases.get(best_disease_id)
            d_map = _as_mapping(disease_obj)
            
            result.update({
                "conclusion": best_disease_id,
                "conclusion_label": d_map.get("nama", best_disease_id),
                "cf": round(best_cf, 3),
                "status": "SUCCESS",
                "disease_info": d_map,
            })
        else:
            # Gunakan ExplanationFacility untuk mendapatkan suggestions
            suggestions = self.explanation.get_suggestions(symptom_ids) if self.explanation else []
            
            status = "FAILED"
            if suggestions:
                status = "NEEDS_MORE_INFO"
            elif fwd_result["used_rules"]:
                status = "INCONCLUSIVE"

            result.update({
                "conclusion": None,
                "cf": best_cf,
                "status": status,
                "suggestions": suggestions,
            })
        
        return result