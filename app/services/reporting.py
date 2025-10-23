# services/reporting.py

"""
Service untuk generate reports dari hasil diagnosis dengan integrasi database.

Menyediakan fungsi untuk:
- Generate PDF reports
- Generate TXT reports
- Export ke CSV
- Enrich report data dari database
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# Optional import for PDF generation
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    FPDF = None

# Import database functions untuk integrasi
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database_manager import load_rules

class ReportingService:
    """Kelas untuk menghasilkan laporan dari hasil diagnosis dengan enrichment dari DB."""

    def __init__(self, output_dir: str = "reports"):
        """Initialize ReportingService.
        
        Args:
            output_dir: Direktori untuk menyimpan reports
        """
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        
        # Load database paths
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        self.symptoms_path = os.path.join(base_path, "symptoms.json")
        self.diseases_path = os.path.join(base_path, "diseases.json")

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file helper."""
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_disease_by_id(self, disease_id: str) -> Optional[Dict[str, Any]]:
        """Ambil detail disease dari database."""
        diseases_list = self._load_json(self.diseases_path)
        
        # Convert list to dict for easier lookup
        if isinstance(diseases_list, list):
            for disease in diseases_list:
                if disease.get('id') == disease_id:
                    return disease
            return None
        else:
            return diseases_list.get(disease_id)
    
    def _get_symptoms_by_ids(self, symptom_ids: List[str]) -> List[Dict[str, Any]]:
        """Ambil detail symptoms dari database."""
        symptoms_list = self._load_json(self.symptoms_path)
        
        # Convert list to dict for easier lookup
        if isinstance(symptoms_list, list):
            symptoms_dict = {s.get('id'): s for s in symptoms_list if 'id' in s}
        else:
            symptoms_dict = symptoms_list
        
        return [
            symptoms_dict.get(sid, {"id": sid, "nama": f"Symptom {sid}"}) 
            for sid in symptom_ids
        ]
    
    def _generate_filename(self, extension: str) -> str:
        """Membuat nama file unik berdasarkan timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"konsultasi_{timestamp}.{extension}")

    def generate_txt_report(
        self, 
        result: Dict[str, Any], 
        symptom_ids: Optional[List[str]] = None,
        user_cf: Optional[float] = None
    ) -> str:
        """
        Membuat laporan TXT dari hasil diagnosis dengan enrichment dari DB.

        Args:
            result (Dict[str, Any]): Dictionary hasil dari engine.diagnose() atau forward_chaining.
            symptom_ids (Optional[List[str]]): List ID gejala yang dipilih (optional).
            user_cf (Optional[float]): User certainty factor (optional).

        Returns:
            str: Path ke file laporan yang telah dibuat.
        """
        filepath = self._generate_filename("txt")
        
        # Get conclusion ID
        conclusion_id = result.get("conclusion")
        
        # Enrich dengan detail dari database
        symptoms_detail = []
        if symptom_ids:
            symptoms_detail = self._get_symptoms_by_ids(symptom_ids)
        else:
            facts = result.get('facts', [])
            if facts:
                symptoms_detail = self._get_symptoms_by_ids(facts)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 40 + "\n")
            f.write("      LAPORAN HASIL KONSULTASI\n")
            f.write("=" * 40 + "\n")
            f.write(f"Tanggal: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\n")
            
            # Symptoms section
            f.write("GEJALA YANG DILAPORKAN:\n")
            if symptoms_detail:
                for symptom in symptoms_detail:
                    symptom_name = symptom.get('nama', symptom.get('name', symptom.get('id')))
                    f.write(f"  - {symptom_name}\n")
            else:
                f.write("  (Tidak ada detail gejala)\n")
            
            if user_cf is not None:
                f.write(f"\nTingkat Keyakinan User: {user_cf * 100:.0f}%\n")
            
            f.write("\n" + "=" * 40 + "\n\n")

            if not conclusion_id:
                f.write("HASIL: Tidak ada penyakit yang dapat disimpulkan dengan pasti.\n")
                f.write("\nSaran: Mohon konsultasi dengan dokter hewan untuk pemeriksaan lebih lanjut.\n")
                return filepath

            # Ambil detail penyakit dari DB
            disease = self._get_disease_by_id(conclusion_id)
            if not disease:
                 f.write(f"HASIL: Penyakit dengan ID '{conclusion_id}' tidak ditemukan di database.\n")
                 return filepath

            disease_name = disease.get('nama', disease.get('name', 'Unknown'))
            f.write(f"--- DIAGNOSIS: {disease_name.upper()} ---\n")
            f.write(f"Tingkat Kepercayaan Sistem: {result.get('cf', 0) * 100:.1f}%\n\n")
            
            if 'penyebab' in disease:
                f.write(f"Penyebab:\n{disease['penyebab']}\n\n")
            
            if 'deskripsi' in disease or 'description' in disease:
                desc = disease.get('deskripsi') or disease.get('description', '')
                f.write(f"Deskripsi:\n{desc}\n\n")
            
            if 'pengobatan' in disease or 'treatment' in disease:
                treatment = disease.get('pengobatan') or disease.get('treatment', '')
                f.write(f"Saran Pengobatan:\n{treatment}\n\n")
            
            if 'pencegahan' in disease or 'prevention' in disease:
                prevention = disease.get('pencegahan') or disease.get('prevention', '')
                f.write(f"Saran Pencegahan:\n{prevention}\n\n")
            
            # Reasoning section
            f.write("=" * 40 + "\n")
            f.write("--- ALUR PENALARAN (HOW) ---\n")
            f.write("=" * 40 + "\n\n")
            
            reasoning_path = result.get('reasoning_path', '')
            if reasoning_path:
                f.write(f"Urutan Aturan: {reasoning_path}\n\n")
            
            used_rules = result.get('used_rules', [])
            if used_rules:
                f.write("Rules yang Digunakan:\n")
                rules = load_rules()
                for rule_id in used_rules:
                    rule = rules.get(rule_id, {})
                    if rule:
                        f.write(f"  - {rule_id}: IF {rule.get('IF')} THEN {rule.get('THEN')} (CF: {rule.get('CF', 1.0)})\n")
                f.write("\n")
            
            trace = result.get('trace', [])
            if trace:
                f.write("Langkah-langkah Detail:\n")
                for step in trace:
                    if isinstance(step, dict):
                        f.write(
                            f"  - Langkah {step.get('step', '?')}: Aturan {step.get('rule', '?')} digunakan "
                            f"karena [{step.get('matched_if', '?')}] terpenuhi. "
                            f"Menghasilkan '{step.get('derived', '?')}' dengan CF {step.get('cf_after', 0):.2f}.\n"
                        )
                    else:
                        f.write(f"  - {step}\n")
        
        return filepath
        
    def generate_pdf_report(
        self, 
        result: Dict[str, Any],
        symptom_ids: Optional[List[str]] = None,
        user_cf: Optional[float] = None
    ) -> str:
        """
        Membuat laporan PDF dari hasil diagnosis.

        Args:
            result (Dict[str, Any]): Dictionary hasil dari engine.diagnose().
            kb (KnowledgeBase): Knowledge Base untuk mengambil detail penyakit.

        Returns:
            str: Path ke file laporan yang telah dibuat.
        
        Raises:
            ImportError: Jika fpdf tidak terinstall.
        """
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf tidak terinstall. Install dengan: pip install fpdf")
        
        filepath = self._generate_filename("pdf")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        
        pdf.cell(0, 10, "Laporan Hasil Konsultasi", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"Tanggal: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", 0, 1, 'C')
        pdf.ln(5)
        
        # Symptoms section
        symptoms_detail = []
        if symptom_ids:
            symptoms_detail = self._get_symptoms_by_ids(symptom_ids)
        else:
            facts = result.get('facts', [])
            if facts:
                symptoms_detail = self._get_symptoms_by_ids(facts)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Gejala yang Dilaporkan:", 0, 1)
        pdf.set_font("Arial", '', 11)
        
        if symptoms_detail:
            symptoms_text = ", ".join([
                s.get('nama', s.get('name', s.get('id')))
                for s in symptoms_detail
            ])
            pdf.multi_cell(0, 5, symptoms_text.encode('latin-1', 'replace').decode('latin-1'))
        else:
            pdf.cell(0, 5, "(Tidak ada detail gejala)", 0, 1)
        
        if user_cf is not None:
            pdf.cell(0, 5, f"Tingkat Keyakinan User: {user_cf * 100:.0f}%", 0, 1)
        
        pdf.ln(5)
        
        conclusion_id = result.get("conclusion")
        if not conclusion_id:
            pdf.set_font("Arial", 'BI', 12)
            pdf.cell(0, 10, "Tidak ada diagnosis pasti yang dapat dibuat.", 0, 1)
            pdf.output(filepath)
            return filepath
            
        disease = self._get_disease_by_id(conclusion_id)
        if not disease:
            pdf.set_font("Arial", 'BI', 12)
            pdf.cell(0, 10, f"Error: Penyakit ID '{conclusion_id}' tidak ditemukan.", 0, 1)
            pdf.output(filepath)
            return filepath
        
        pdf.set_font("Arial", 'B', 14)
        disease_name = disease.get('nama', disease.get('name', 'Unknown'))
        pdf.cell(0, 10, f"Hasil Diagnosis: {disease_name}", 0, 1)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"Tingkat Kepercayaan: {result.get('cf', 0) * 100:.1f}%", 0, 1)
        pdf.ln(5)

        # Helper untuk menulis section
        def write_section(title, content):
            if not content:
                return
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, title, 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 5, content.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(4)
        
        write_section("Penyebab", disease.get('penyebab', ''))
        write_section("Deskripsi", disease.get('deskripsi', disease.get('description', '')))
        write_section("Saran Pengobatan", disease.get('pengobatan', disease.get('treatment', '')))
        write_section("Saran Pencegahan", disease.get('pencegahan', disease.get('prevention', '')))
        
        # Rules used
        used_rules = result.get('used_rules', [])
        if used_rules:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "Rules yang Digunakan:", 0, 1)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 5, ", ".join(used_rules))

        pdf.output(filepath)
        return filepath
    
    def generate_report_from_consultation(
        self,
        consultation_data: Dict[str, Any],
        format: str = "pdf"
    ) -> str:
        """Generate report dari consultation data yang sudah ada.
        
        Args:
            consultation_data: Dictionary consultation data dari StorageService
            format: Format report ('pdf' atau 'txt')
            
        Returns:
            Path ke file report yang dibuat
        """
        # Extract data dari consultation
        symptom_ids = consultation_data.get('symptoms', {}).get('ids', [])
        diagnosis = consultation_data.get('diagnosis', {})
        user_cf = consultation_data.get('user_cf', 0.8)
        
        # Build result dict for report generation
        result = {
            "conclusion": diagnosis.get('conclusion_id'),
            "cf": diagnosis.get('cf', 0.0),
            "method": diagnosis.get('method', 'forward'),
            "used_rules": diagnosis.get('used_rules', []),
            "reasoning_path": diagnosis.get('reasoning_path', ''),
            "trace": consultation_data.get('trace', []),
            "facts": symptom_ids
        }
        
        if format.lower() == "pdf":
            return self.generate_pdf_report(result, symptom_ids, user_cf)
        else:
            return self.generate_txt_report(result, symptom_ids, user_cf)


# Contoh penggunaan
if __name__ == "__main__":
    reporting = ReportingService()
    
    # Test generate report
    test_result = {
        "conclusion": "P1",
        "cf": 0.85,
        "method": "forward",
        "used_rules": ["R1", "R2"],
        "reasoning_path": "R1 -> R2",
        "trace": [],
        "facts": ["G1", "G2"]
    }
    
    txt_path = reporting.generate_txt_report(
        result=test_result,
        symptom_ids=["G1", "G2"],
        user_cf=0.9
    )
    print(f"✅ TXT report generated: {txt_path}")
    
    try:
        pdf_path = reporting.generate_pdf_report(
            result=test_result,
            symptom_ids=["G1", "G2"],
            user_cf=0.9
        )
        print(f"✅ PDF report generated: {pdf_path}")
    except Exception as e:
        print(f"⚠️ PDF generation failed (fpdf might not be installed): {e}")