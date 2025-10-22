"""
Explanation Module
Generate penjelasan untuk hasil diagnosis sistem pakar
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import os

@dataclass
class ExplanationTrace:
    """Trace satu langkah inferensi"""
    rule_id: str
    symptoms_matched: List[str]
    disease_id: str
    rule_cf: float
    combined_cf: float
    explanation_text: str

class ExplanationGenerator:
    """
    Generator penjelasan untuk hasil diagnosis
    Menjelaskan kenapa sistem menghasilkan diagnosis tertentu
    """
    
    def __init__(self, symptoms_path="database/symptoms.json", 
                 diseases_path="database/diseases.json",
                 rules_path="database/rules.json"):
        self.symptoms_data = self._load_json(symptoms_path)
        self.diseases_data = self._load_json(diseases_path)
        self.rules_data = self._load_json(rules_path)
        self.traces: List[ExplanationTrace] = []
    
    def _load_json(self, filepath: str) -> any:
        """Load data dari file JSON"""
        if not os.path.exists(filepath):
            return [] if "symptoms" in filepath or "diseases" in filepath else {}
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_symptom_name(self, symptom_id: str) -> str:
        """Ambil nama gejala dari ID"""
        for symptom in self.symptoms_data:
            if symptom["id"] == symptom_id:
                return symptom["nama"]
        return symptom_id
    
    def get_disease_name(self, disease_id: str) -> str:
        """Ambil nama penyakit dari ID"""
        for disease in self.diseases_data:
            if disease["id"] == disease_id:
                return disease["nama"]
        return disease_id
    
    def get_disease_info(self, disease_id: str) -> Optional[Dict]:
        """Ambil informasi lengkap penyakit"""
        for disease in self.diseases_data:
            if disease["id"] == disease_id:
                return disease
        return None
    
    def add_trace(self, rule_id: str, symptoms_matched: List[str], 
                  disease_id: str, rule_cf: float, combined_cf: float) -> None:
        """
        Tambahkan trace untuk satu langkah inferensi
        
        Args:
            rule_id: ID rule yang digunakan
            symptoms_matched: List gejala yang cocok
            disease_id: Penyakit yang diinfer
            rule_cf: CF dari rule
            combined_cf: CF gabungan setelah kombinasi
        """
        symptom_names = [self.get_symptom_name(sid) for sid in symptoms_matched]
        disease_name = self.get_disease_name(disease_id)
        
        explanation = (
            f"Berdasarkan Rule {rule_id}: "
            f"Karena ditemukan gejala {', '.join(symptom_names)}, "
            f"maka sistem mendeteksi kemungkinan penyakit {disease_name} "
            f"dengan tingkat keyakinan {rule_cf:.2f} (CF Rule). "
            f"Setelah dikombinasikan dengan inferensi sebelumnya, "
            f"CF menjadi {combined_cf:.2f}."
        )
        
        trace = ExplanationTrace(
            rule_id=rule_id,
            symptoms_matched=symptoms_matched,
            disease_id=disease_id,
            rule_cf=rule_cf,
            combined_cf=combined_cf,
            explanation_text=explanation
        )
        self.traces.append(trace)
    
    def generate_full_explanation(self, working_memory) -> str:
        """
        Generate penjelasan lengkap untuk hasil diagnosis
        
        Args:
            working_memory: Instance WorkingMemory
            
        Returns:
            String penjelasan lengkap
        """
        explanation_parts = []
        
        # 1. Gejala yang diinput user
        symptoms = working_memory.get_all_symptoms()
        if symptoms:
            symptom_names = [self.get_symptom_name(sid) for sid in symptoms]
            explanation_parts.append("📋 **Gejala yang Diidentifikasi:**")
            for i, name in enumerate(symptom_names, 1):
                cf = working_memory.get_symptom_cf(symptoms[i-1])
                explanation_parts.append(f"  {i}. {name} (CF: {cf:.2f})")
            explanation_parts.append("")
        
        # 2. Proses inferensi
        if self.traces:
            explanation_parts.append("🔍 **Proses Inferensi:**")
            for i, trace in enumerate(self.traces, 1):
                explanation_parts.append(f"\n**Langkah {i}:**")
                explanation_parts.append(trace.explanation_text)
            explanation_parts.append("")
        
        # 3. Hasil diagnosis
        results = working_memory.get_diagnosis_results()
        if results:
            explanation_parts.append("🎯 **Hasil Diagnosis:**")
            for i, result in enumerate(results, 1):
                disease_name = self.get_disease_name(result['disease_id'])
                cf = result['cf']
                confidence_level = self._get_confidence_level(cf)
                explanation_parts.append(
                    f"  {i}. **{disease_name}** - "
                    f"Tingkat Keyakinan: {cf:.2%} ({confidence_level})"
                )
            explanation_parts.append("")
        
        # 4. Informasi penyakit teratas
        top_disease = working_memory.get_top_disease()
        if top_disease:
            disease_info = self.get_disease_info(top_disease['disease_id'])
            if disease_info:
                explanation_parts.append("📖 **Informasi Penyakit Terdeteksi:**")
                explanation_parts.append(f"**Nama:** {disease_info['nama']}")
                explanation_parts.append(f"**Penyebab:** {disease_info['penyebab']}")
                explanation_parts.append(f"**Deskripsi:** {disease_info['deskripsi']}")
                explanation_parts.append(f"**Pengobatan:** {disease_info['pengobatan']}")
                explanation_parts.append(f"**Pencegahan:** {disease_info['pencegahan']}")
        
        return "\n".join(explanation_parts)
    
    def _get_confidence_level(self, cf: float) -> str:
        """Konversi CF menjadi level keyakinan dalam bahasa"""
        if cf >= 0.8:
            return "Sangat Yakin"
        elif cf >= 0.6:
            return "Yakin"
        elif cf >= 0.4:
            return "Cukup Yakin"
        elif cf >= 0.2:
            return "Kurang Yakin"
        else:
            return "Tidak Yakin"
    
    def generate_short_summary(self, working_memory) -> str:
        """
        Generate ringkasan singkat hasil diagnosis
        
        Returns:
            String ringkasan singkat
        """
        top = working_memory.get_top_disease()
        if not top:
            return "Tidak ada penyakit yang terdeteksi berdasarkan gejala yang diberikan."
        
        disease_name = self.get_disease_name(top['disease_id'])
        cf = top['cf']
        confidence_level = self._get_confidence_level(cf)
        
        return (
            f"Sistem mendeteksi kemungkinan **{disease_name}** "
            f"dengan tingkat keyakinan {cf:.2%} ({confidence_level})."
        )
    
    def generate_why_explanation(self, disease_id: str, working_memory) -> str:
        """
        Jelaskan kenapa penyakit tertentu terdeteksi (WHY explanation)
        
        Args:
            disease_id: ID penyakit yang ingin dijelaskan
            working_memory: Instance WorkingMemory
            
        Returns:
            Penjelasan kenapa penyakit tersebut terdeteksi
        """
        relevant_traces = [t for t in self.traces if t.disease_id == disease_id]
        
        if not relevant_traces:
            return f"Tidak ada rule yang mengarah ke penyakit {self.get_disease_name(disease_id)}."
        
        explanation = [f"**Kenapa sistem mendeteksi {self.get_disease_name(disease_id)}?**\n"]
        
        for trace in relevant_traces:
            symptom_names = [self.get_symptom_name(sid) for sid in trace.symptoms_matched]
            explanation.append(
                f"- Karena ditemukan gejala: {', '.join(symptom_names)} "
                f"(Rule {trace.rule_id}, CF: {trace.rule_cf:.2f})"
            )
        
        final_cf = working_memory.inferred_diseases.get(disease_id, 0)
        explanation.append(f"\nTingkat keyakinan akhir: {final_cf:.2%}")
        
        return "\n".join(explanation)
    
    def generate_how_to_improve(self, working_memory) -> str:
        """
        Saran bagaimana meningkatkan akurasi diagnosis (HOW TO IMPROVE)
        
        Returns:
            Saran untuk user
        """
        symptoms_count = len(working_memory.get_all_symptoms())
        results = working_memory.get_diagnosis_results()
        
        suggestions = ["💡 **Saran untuk Meningkatkan Akurasi:**\n"]
        
        if symptoms_count < 3:
            suggestions.append(
                "- Coba tambahkan lebih banyak gejala yang diamati. "
                "Semakin banyak gejala yang akurat, semakin tepat diagnosis."
            )
        
        if not results:
            suggestions.append(
                "- Tidak ada penyakit yang terdeteksi. Pastikan gejala yang "
                "diinput sesuai dengan kondisi ikan yang diamati."
            )
        elif results and results[0]['cf'] < 0.6:
            suggestions.append(
                "- Tingkat keyakinan masih rendah. Periksa kembali gejala "
                "dan tambahkan gejala lain yang mungkin terlewat."
            )
        
        suggestions.append(
            "- Jika ragu, konsultasikan dengan ahli perikanan atau dokter hewan."
        )
        
        return "\n".join(suggestions)
    
    def clear_traces(self) -> None:
        """Clear semua trace (untuk diagnosis baru)"""
        self.traces.clear()
    
    def export_trace_log(self) -> List[Dict]:
        """Export trace dalam format JSON untuk logging"""
        return [
            {
                "rule_id": trace.rule_id,
                "symptoms_matched": trace.symptoms_matched,
                "disease_id": trace.disease_id,
                "rule_cf": trace.rule_cf,
                "combined_cf": trace.combined_cf,
                "explanation": trace.explanation_text
            }
            for trace in self.traces
        ]