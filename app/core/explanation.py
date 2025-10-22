

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ReasoningStep:
    """Representasi satu langkah penalaran (PINDAH DARI inference_engine.py)."""
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
        """Convert ke format dict untuk UI."""
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


class ExplanationFacility:
    """Fasilitas penjelasan untuk sistem pakar.
    
    Menyediakan dua jenis penjelasan:
    1. WHY: Mengapa sistem bertanya tentang gejala tertentu
    2. HOW: Bagaimana sistem sampai pada kesimpulan tertentu
    """
    
    def __init__(self, rules: Dict[str, Dict[str, Any]], kb: Any):
        self.rules = rules
        self.kb = kb
        self.trace: List[ReasoningStep] = []
        self.current_goal: Optional[str] = None
    
    # ============== WHY EXPLANATION ==============
    
    def explain_why_asking(
        self, 
        symptom_id: str, 
        current_goal: Optional[str] = None
    ) -> str:
        """Jelaskan mengapa sistem bertanya tentang gejala ini.
        
        Contoh output:
        "Sistem menanyakan gejala 'bintik putih' karena sedang menelusuri 
         kemungkinan penyakit White Spot (P1). Gejala ini digunakan dalam 
         aturan R1 dengan tingkat kepercayaan 90%."
        """
        # Cari rules yang menggunakan symptom ini
        relevant_rules = [
            (rid, rule) 
            for rid, rule in self.rules.items() 
            if symptom_id in rule.get("IF", [])
        ]
        
        if not relevant_rules:
            return f"Gejala '{symptom_id}' tidak ditemukan dalam basis pengetahuan."
        
        # Build explanation
        explanations = []
        for rid, rule in relevant_rules:
            disease_id = rule.get("THEN")
            disease = self.kb.diseases.get(disease_id)
            disease_name = disease.nama if disease else disease_id
            cf = rule.get("CF", 1.0)
            
            exp = (
                f"• Aturan {rid}: Gejala ini digunakan untuk mendiagnosis "
                f"**{disease_name}** dengan CF {cf*100:.0f}%"
            )
            
            # Tambahkan info goal jika ada
            if current_goal and disease_id == current_goal:
                exp += " ← **Target saat ini**"
            
            explanations.append(exp)
        
        header = f"**Mengapa menanyakan gejala ini?**\n\n"
        return header + "\n".join(explanations)
    
    def explain_why_rule(self, rule_id: str) -> str:
        """Jelaskan mengapa aturan ini digunakan."""
        rule = self.rules.get(rule_id)
        if not rule:
            return f"Aturan {rule_id} tidak ditemukan."
        
        antecedents = rule.get("IF", [])
        consequent = rule.get("THEN")
        cf = rule.get("CF", 1.0)
        why_text = rule.get("ask_why", "")
        source = rule.get("source", "Tidak tercatat")
        
        # Get disease info
        disease = self.kb.diseases.get(consequent)
        disease_name = disease.nama if disease else consequent
        
        explanation = f"""
**Aturan {rule_id}**

**JIKA:**
{self._format_antecedents(antecedents)}

**MAKA:** {disease_name} (CF: {cf*100:.0f}%)

**Alasan:** {why_text or "Kombinasi gejala ini merupakan indikator kuat."}

**Sumber:** {source}
"""
        return explanation.strip()
    
    # ============== HOW EXPLANATION ==============
    
    def explain_how_conclusion(
        self, 
        conclusion: str, 
        trace: List[Dict[str, Any]]
    ) -> str:
        """Jelaskan bagaimana sistem sampai pada kesimpulan.
        
        Contoh output:
        "Sistem menyimpulkan penyakit White Spot dengan kepercayaan 85% 
         melalui langkah-langkah berikut:
         1. [Step 1] ...
         2. [Step 2] ..."
        """
        disease = self.kb.diseases.get(conclusion)
        disease_name = disease.nama if disease else conclusion
        
        if not trace:
            return f"Tidak ada trace untuk kesimpulan {disease_name}."
        
        # Header
        final_cf = trace[-1].get("cf_after", 0.0) if trace else 0.0
        explanation = f"""
**Bagaimana sistem menyimpulkan {disease_name}?**

Tingkat Kepercayaan Akhir: **{final_cf*100:.1f}%**

**Langkah Penalaran:**

"""
        
        # Step by step
        for step_data in trace:
            step_num = step_data.get("step")
            rule = step_data.get("rule")
            matched = step_data.get("matched_if", "")
            derived = step_data.get("derived")
            cf_after = step_data.get("cf_after", 0.0)
            
            rule_obj = self.rules.get(rule, {})
            rule_cf = rule_obj.get("CF", 1.0)
            
            explanation += f"""
**Langkah {step_num}:** Aturan {rule}
- Gejala yang cocok: {matched}
- Kesimpulan: {derived}
- CF aturan: {rule_cf*100:.0f}%
- CF hasil: {cf_after*100:.1f}%

"""
        
        return explanation.strip()
    
    def explain_full_reasoning(self, result: Dict[str, Any]) -> str:
        """Generate penjelasan lengkap untuk hasil diagnosis."""
        conclusion = result.get("conclusion")
        if not conclusion:
            return "Tidak ada kesimpulan yang cukup kuat."
        
        cf = result.get("cf", 0.0)
        trace = result.get("trace", [])
        recommendation = result.get("recommendation", "")
        
        # Build comprehensive explanation
        explanation = self.explain_how_conclusion(conclusion, trace)
        
        if recommendation:
            explanation += f"\n\n**Rekomendasi:** {recommendation}"
        
        return explanation
    
    # ============== HELPER METHODS ==============
    
    def _format_antecedents(self, antecedents: List[str]) -> str:
        """Format daftar antecedents untuk display."""
        formatted = []
        for ant in antecedents:
            symptom = self.kb.symptoms.get(ant)
            name = symptom.name if symptom else ant
            formatted.append(f"  - {name} ({ant})")
        return "\n".join(formatted)
    
    def set_current_goal(self, goal: str) -> None:
        """Set goal saat ini untuk konteks WHY."""
        self.current_goal = goal
    
    def add_trace_step(self, step: ReasoningStep) -> None:
        """Tambahkan step ke trace internal."""
        self.trace.append(step)
    
    def get_trace_formatted(self) -> List[Dict[str, Any]]:
        """Ambil trace dalam format UI-friendly."""
        return [step.to_row() for step in self.trace]
    
    def clear_trace(self) -> None:
        """Reset trace."""
        self.trace.clear()
        self.current_goal = None
