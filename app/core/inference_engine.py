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
        """Loop inferensi (EXTRACTED METHOD).
        
        Memisahkan loop logic dari public API.
        """
        used_rules = []
        fired = True
        step_no = 0
        max_steps = limit if limit is not None else max(50, len(rules) * 3)
        
        while fired and step_no < max_steps:
            fired = False
            
            for rid, rule in rules.items():
                # Check if rule can fire
                if not self._can_fire_rule(rule):
                    continue
                
                # Fire rule
                fired_data = self._fire_rule(rid, rule, step_no + 1)
                if fired_data:
                    fired = True
                    step_no += 1
                    used_rules.append(rid)
        
        return used_rules
    
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
    
    def get_rules_details(
        self,
        rule_ids: List[str],
        kb: Any
    ) -> List[Dict[str, Any]]:
        """Get detailed info for list of rules.
        
        Args:
            rule_ids: List of rule IDs
            kb: Knowledge base object
            
        Returns:
            List of rule details with full information
        """
        rules = getattr(kb, "rules", {})
        symptoms = getattr(kb, "symptoms", {})
        
        # Remove duplicates while preserving order
        unique_rule_ids = list(dict.fromkeys(rule_ids))
        
        rule_details = []
        for rid in unique_rule_ids:
            rule = rules.get(rid)
            if not rule:
                continue
            
            if isinstance(rule, dict):
                antecedents = rule.get('IF', [])
                consequent = rule.get('THEN', '')
                cf = rule.get('CF', 1.0)
            else:
                antecedents = getattr(rule, 'IF', [])
                consequent = getattr(rule, 'THEN', '')
                cf = getattr(rule, 'CF', 1.0)
            
            # Get symptom names for antecedents
            antecedent_names = []
            for sid in antecedents:
                symptom_obj = symptoms.get(sid)
                if isinstance(symptom_obj, dict):
                    symptom_name = symptom_obj.get('nama', symptom_obj.get('name', sid))
                else:
                    symptom_name = getattr(symptom_obj, 'nama', sid) if symptom_obj else sid
                antecedent_names.append(symptom_name)
            
            rule_details.append({
                "id": rid,
                "if": antecedents,
                "if_names": antecedent_names,
                "then": consequent,
                "cf": cf
            })
        
        return rule_details
    
    def get_symptom_details(
        self,
        symptom_ids: List[str],
        kb: Any
    ) -> List[Dict[str, str]]:
        """Get detailed info for list of symptoms.
        
        Args:
            symptom_ids: List of symptom IDs
            kb: Knowledge base object
            
        Returns:
            List of symptom details with id and nama
        """
        symptoms = getattr(kb, "symptoms", {})
        symptom_details = []
        
        for sid in symptom_ids:
            symptom_obj = symptoms.get(sid)
            if isinstance(symptom_obj, dict):
                symptom_name = symptom_obj.get('nama', symptom_obj.get('name', sid))
            else:
                symptom_name = getattr(symptom_obj, 'nama', sid) if symptom_obj else sid
            
            symptom_details.append({
                "id": sid,
                "nama": symptom_name
            })
        
        return symptom_details
    
    def get_suggestions(
        self,
        symptom_ids: List[str],
        kb: Any
    ) -> List[Dict[str, Any]]:
        """Dapatkan suggestions untuk gejala yang hampir cocok (partial matching).
        
        Args:
            symptom_ids: List of symptom IDs selected by user
            kb: Knowledge base object
            
        Returns:
            List of suggestions, each containing:
            - disease_id: Disease ID
            - disease_name: Disease name
            - matched_count: Number of matched symptoms
            - total_required: Total symptoms required
            - percentage: Match percentage
            - missing_symptom_ids: List of missing symptom IDs
            - missing_symptom_names: List of missing symptom names
        """
        suggestions = []
        selected_set = set(symptom_ids)
        
        rules = getattr(kb, "rules", {})
        symptoms = getattr(kb, "symptoms", {})
        diseases = getattr(kb, "diseases", {})
        
        for rid, rule in rules.items():
            if isinstance(rule, dict):
                required_symptoms = rule.get('IF', [])
                disease_id = rule.get('THEN')
            else:
                required_symptoms = getattr(rule, 'IF', [])
                disease_id = getattr(rule, 'THEN', None)
            
            if not required_symptoms or not disease_id:
                continue
            
            required_set = set(required_symptoms)
            matched = selected_set.intersection(required_set)
            missing = required_set - selected_set
            
            # Hanya tampilkan jika ada kecocokan parsial
            if len(matched) > 0 and len(missing) > 0:
                # Get disease name
                disease_obj = diseases.get(disease_id)
                if isinstance(disease_obj, dict):
                    disease_name = disease_obj.get('nama', disease_obj.get('name', disease_id))
                else:
                    disease_name = getattr(disease_obj, 'nama', disease_id) if disease_obj else disease_id
                
                # Get missing symptom names
                missing_names = []
                for sid in missing:
                    symptom_obj = symptoms.get(sid)
                    if isinstance(symptom_obj, dict):
                        symptom_name = symptom_obj.get('nama', symptom_obj.get('name', sid))
                    else:
                        symptom_name = getattr(symptom_obj, 'nama', sid) if symptom_obj else sid
                    missing_names.append(symptom_name)
                
                suggestions.append({
                    'disease_id': disease_id,
                    'disease_name': disease_name,
                    'matched_count': len(matched),
                    'total_required': len(required_set),
                    'percentage': len(matched) / len(required_set) * 100,
                    'missing_symptom_ids': list(missing),
                    'missing_symptom_names': missing_names,
                    'current_symptoms': list(matched),  # Gejala yang sudah cocok
                    'rule_id': rid,  # Untuk tracking
                })
        
        # Sort by percentage match (descending)
        suggestions.sort(key=lambda x: x['percentage'], reverse=True)
        
        return suggestions
    
    def diagnose(
        self,
        symptom_ids: List[str],
        user_cf: float,
        kb: Any,
    ) -> Dict[str, Any]:
        """High-level diagnosis pipeline for frontend.
        
        Builds initial facts from symptoms, runs forward chaining,
        selects best disease above threshold, and returns complete result.
        
        Args:
            symptom_ids: List of symptom IDs selected by user
            user_cf: User's certainty factor (0.0 - 1.0)
            kb: Knowledge base object dengan attributes:
                - rules: Dict[str, Rule]
                - symptoms: Dict[str, Symptom]
                - diseases: Dict[str, Disease]
        
        Returns:
            Dict with keys:
            - method: "forward"
            - facts: List of initial fact IDs
            - trace: List of reasoning steps
            - used_rules: List of rule IDs used
            - reasoning_path: String of rules used
            - conclusion: Disease ID (or None)
            - conclusion_label: Disease name
            - cf: Final confidence factor
            - recommendation: Treatment recommendation
            - prevention: List of prevention tips
        """
        # Helper function untuk konversi object ke dict
        def _as_mapping(obj: Any) -> Dict[str, Any]:
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            # pydantic v1/v2
            for attr in ("model_dump", "dict"):
                if hasattr(obj, attr):
                    try:
                        return getattr(obj, attr)()
                    except Exception:
                        pass
            # dataclass or simple object
            if hasattr(obj, "__dict__"):
                return dict(obj.__dict__)
            return {}
        
        # Convert rules ke dict format
        rules = {}
        for rid, r in getattr(kb, "rules", {}).items():
            rules[rid] = _as_mapping(r)
        
        # Build initial facts dengan user CF dan symptom weights
        initial_facts_cf: Dict[str, float] = {}
        user_cf_clamped = min(1.0, max(0.0, user_cf or 1.0))
        
        symptoms_map = getattr(kb, "symptoms", {})
        for sid in symptom_ids:
            s_obj = symptoms_map.get(sid)
            s_map = _as_mapping(s_obj)
            weight = float(s_map.get("weight", 1.0))
            # CF awal = user_cf * weight gejala
            initial_facts_cf[sid] = min(1.0, max(0.0, user_cf_clamped * weight))
        
        # Run forward chaining
        fwd_result = self.forward_chaining(rules, initial_facts_cf, kb)
        
        # Get diseases dari KB
        diseases = getattr(kb, "diseases", {})
        
        # Cari disease terbaik dari conclusions
        best_disease_id: Optional[str] = None
        best_cf = 0.0
        
        for disease_id in diseases.keys():
            cf = float(fwd_result["conclusions"].get(disease_id, 0.0))
            if cf > best_cf:
                best_cf = cf
                best_disease_id = disease_id
        
        # Build result
        trace_rows = fwd_result.get("trace", [])
        used_rules = fwd_result.get("used_rules", [])
        reasoning_path = fwd_result.get("reasoning_path", "")
        
        # Get symptom details untuk frontend
        symptom_details = self.get_symptom_details(symptom_ids, kb)
        
        # Get rules details untuk frontend
        rules_details = self.get_rules_details(used_rules, kb) if used_rules else []
        
        result: Dict[str, Any] = {
            "method": "forward",
            "facts": list(initial_facts_cf.keys()),
            "trace": trace_rows,
            "used_rules": used_rules,
            "reasoning_path": reasoning_path,
            # Data untuk frontend (no logic needed)
            "symptom_details": symptom_details,
            "rules_details": rules_details,
        }
        
        # Jika ada conclusion di atas threshold
        if best_disease_id and best_cf >= self.threshold:
            disease_obj = diseases.get(best_disease_id)
            d_map = _as_mapping(disease_obj)
            
            # Cari recommendation dari rule terakhir yang fired untuk disease ini
            recommendation: Optional[str] = None
            for rid in reversed(used_rules):
                rmap = rules.get(rid, {})
                if rmap.get("THEN") == best_disease_id:
                    recommendation = rmap.get("recommendation") or None
                    if recommendation:
                        break
            
            # Jika tidak ada recommendation dari rule, gunakan treatment pertama
            if not recommendation:
                treatments = d_map.get("pengobatan") or d_map.get("treatments") or ""
                if isinstance(treatments, list) and treatments:
                    recommendation = treatments[0]
                elif isinstance(treatments, str):
                    recommendation = treatments
            
            # Get prevention
            prevention = d_map.get("pencegahan") or d_map.get("prevention") or []
            if isinstance(prevention, str):
                prevention = [prevention]
            
            result.update({
                "conclusion": best_disease_id,
                "conclusion_label": d_map.get("nama") or d_map.get("name") or best_disease_id,
                "cf": round(best_cf, 3),
                "status": "SUCCESS",
                "recommendation": recommendation,
                "prevention": prevention,
                # Tambahkan info lengkap untuk frontend
                "disease_info": {
                    "id": best_disease_id,
                    "nama": d_map.get("nama") or d_map.get("name", ""),
                    "penyebab": d_map.get("penyebab", ""),
                    "deskripsi": d_map.get("deskripsi") or d_map.get("description", ""),
                    "pengobatan": d_map.get("pengobatan", ""),
                    "pencegahan": d_map.get("pencegahan", ""),
                },
            })
        else:
            # Tidak ada conclusion yang cukup kuat
            suggestions = self.get_suggestions(symptom_ids, kb)
            
            # Tentukan status berdasarkan hasil
            status = "FAILED"
            if suggestions:
                status = "NEEDS_MORE_INFO"
            elif fwd_result["used_rules"]:
                status = "INCONCLUSIVE"

            result.update({
                "conclusion": None,
                "cf": best_cf, # Kembalikan CF tertinggi meskipun di bawah threshold
                "status": status,
                "recommendation": None,
                "prevention": [],
                "suggestions": suggestions,
            })
        
        return result