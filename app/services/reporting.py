# services/reporting.py

import os
from datetime import datetime
from typing import Dict, Any
from fpdf import FPDF
from core.models import KnowledgeBase # Impor KnowledgeBase

class ReportingService:
    """Kelas untuk menghasilkan laporan dari hasil diagnosis terstruktur."""

    def __init__(self, output_dir: str = "reports"):
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

    def _generate_filename(self, extension: str) -> str:
        """Membuat nama file unik berdasarkan timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"konsultasi_{timestamp}.{extension}")

    def generate_txt_report(self, result: Dict[str, Any], kb: KnowledgeBase) -> str:
        """
        Membuat laporan TXT dari hasil diagnosis.

        Args:
            result (Dict[str, Any]): Dictionary hasil dari engine.diagnose().
            kb (KnowledgeBase): Knowledge Base untuk mengambil detail penyakit.

        Returns:
            str: Path ke file laporan yang telah dibuat.
        """
        filepath = self._generate_filename("txt")
        conclusion_id = result.get("conclusion")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 40 + "\n")
            f.write("      LAPORAN HASIL KONSULTASI\n")
            f.write("=" * 40 + "\n")
            f.write(f"Tanggal: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n\n")
            f.write(f"Gejala yang Diberikan: {', '.join(result.get('facts', []))}\n\n")

            if not conclusion_id:
                f.write("HASIL: Tidak ada penyakit yang dapat disimpulkan dengan pasti.\n")
                return filepath

            # Ambil detail penyakit dari KB
            disease = kb.diseases.get(conclusion_id)
            if not disease:
                 f.write(f"HASIL: Penyakit dengan ID '{conclusion_id}' tidak ditemukan di database.\n")
                 return filepath

            f.write(f"--- DIAGNOSIS: {disease.nama.upper()} ---\n")
            f.write(f"Tingkat Kepercayaan: {result.get('cf', 0) * 100:.1f}%\n\n")
            f.write(f"Penyebab: {disease.penyebab}\n\n")
            f.write(f"Deskripsi:\n{disease.deskripsi}\n\n")
            f.write(f"Saran Pengobatan:\n{disease.pengobatan}\n\n")
            f.write(f"Saran Pencegahan:\n{disease.pencegahan}\n\n")
            
            f.write("--- Alur Penalaran (HOW) ---\n")
            f.write(f"Urutan Aturan: {result.get('reasoning_path')}\n\n")
            f.write("Langkah-langkah Detail:\n")
            for step in result.get('trace', []):
                f.write(
                    f"  - Langkah {step['step']}: Aturan {step['rule']} digunakan "
                    f"karena [{step['matched_if']}] terpenuhi. "
                    f"Menghasilkan '{step['derived']}' dengan CF baru {step['cf_after']:.2f}.\n"
                )
        return filepath
        
    def generate_pdf_report(self, result: Dict[str, Any], kb: KnowledgeBase) -> str:
        """
        Membuat laporan PDF dari hasil diagnosis.

        Args:
            result (Dict[str, Any]): Dictionary hasil dari engine.diagnose().
            kb (KnowledgeBase): Knowledge Base untuk mengambil detail penyakit.

        Returns:
            str: Path ke file laporan yang telah dibuat.
        """
        filepath = self._generate_filename("pdf")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        
        pdf.cell(0, 10, "Laporan Hasil Konsultasi", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"Tanggal: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", 0, 1, 'C')
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Gejala yang Dilaporkan:", 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 5, ", ".join(result.get('facts', [])).encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
        
        conclusion_id = result.get("conclusion")
        if not conclusion_id:
            pdf.set_font("Arial", 'BI', 12)
            pdf.cell(0, 10, "Tidak ada diagnosis pasti yang dapat dibuat.", 0, 1)
            pdf.output(filepath)
            return filepath
            
        disease = kb.diseases.get(conclusion_id)
        if not disease:
            pdf.set_font("Arial", 'BI', 12)
            pdf.cell(0, 10, f"Error: Penyakit ID '{conclusion_id}' tidak ditemukan.", 0, 1)
            pdf.output(filepath)
            return filepath
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Hasil Diagnosis: {disease.nama}", 0, 1)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"Tingkat Kepercayaan: {result.get('cf', 0) * 100:.1f}%", 0, 1)
        pdf.ln(5)

        # Helper untuk menulis section
        def write_section(title, content):
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, title, 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 5, content.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(4)
        
        write_section("Penyebab", disease.penyebab)
        write_section("Deskripsi", disease.deskripsi)
        write_section("Saran Pengobatan", disease.pengobatan)
        write_section("Saran Pencegahan", disease.pencegahan)

        pdf.output(filepath)
        return filepath