"""Inference Engine.

Modul ini mengkoordinasikan komponen-komponen:
- WorkingMemory: Kelola fakta dan CF
- ExplanationFacility: Generate penjelasan WHY/HOW
- InferenceEngine: Orchestrator untuk forward/backward chaining
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

# Import dari modul baru
from .working_memory import WorkingMemory
from .explanation import ExplanationFacility, ReasoningStep


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
    
    # ... backward_chaining juga disederhanakan serupa ...
    
    def diagnose(
        self,
        symptom_ids: List[str],
        user_cf: float,
        kb: Any,
    ) -> Dict[str, Any]:
        """High-level diagnosis (UNCHANGED INTERFACE).
        
        API tetap sama untuk frontend, tapi internal menggunakan
        WorkingMemory dan ExplanationFacility.
        """
        # ... implementasi serupa tapi menggunakan komponen baru ...