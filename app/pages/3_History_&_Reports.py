import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# Backend imports
from database.database_manager import DatabaseManager
from services.storage import StorageService
from services.logging_service import LoggingService
from services.reporting import ReportingService

# UI imports
from ui.theming import page_header

@st.cache_resource
def get_db():
    # Get absolute path to database directory
    db_path = Path(__file__).parent.parent / "database"
    db = DatabaseManager(db_path)
    db.load_all()
    return db

@st.cache_resource
def get_storage():
    return StorageService()

@st.cache_resource
def get_logger():
    return LoggingService()

@st.cache_resource
def get_reporter():
    return ReportingService(output_dir="reports")

def run():
    page_header("History & Reports", "Riwayat konsultasi dan ekspor laporan.")
    
    # Get backend instances
    db = get_db()
    storage = get_storage()
    logger = get_logger()
    reporter = get_reporter()
    
    tab1, tab2, tab3 = st.tabs(["📜 History", "📊 Statistics", "📥 Export"])
    
    # ===== TAB 1: History =====
    with tab1:
        st.subheader("Riwayat Konsultasi")
        
        # Load history
        col1, col2 = st.columns([3, 1])
        with col1:
            limit = st.slider("Jumlah record yang ditampilkan", 5, 50, 10)
        with col2:
            if st.button("🔄 Refresh"):
                st.cache_resource.clear()
                st.rerun()
        
        history = storage.load_consultation_history(limit=limit)
        
        if history:
            # Display as table
            history_data = []
            for i, cons in enumerate(history, 1):
                diagnosis = cons.get("diagnosis", {})
                # FIX: Menggunakan 'conclusion' bukan 'disease_id'
                disease_id = diagnosis.get("conclusion", "N/A")
                
                # Enrich with disease name from database
                disease_name = "Unknown"
                if disease_id and disease_id != "N/A" and disease_id in db.diseases:
                    disease_name = db.diseases[disease_id].nama
                elif diagnosis.get("status") == "FAILED":
                    disease_name = "Failed"
                elif diagnosis.get("status") == "INCONCLUSIVE":
                    disease_name = "Inconclusive"

                symptoms = cons.get("symptoms", {}).get("ids", [])
                
                history_data.append({
                    "#": i,
                    "Timestamp": cons.get("timestamp", "N/A")[:19].replace("T", " "),
                    "Symptoms": ", ".join(symptoms[:3]) + ("..." if len(symptoms) > 3 else ""),
                    "Disease": disease_name,
                    "CF": f"{diagnosis.get('cf', 0.0):.2%}",
                    "Method": diagnosis.get("method", "N/A").upper()
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, width="stretch", hide_index=True)

            # Search functionality
            st.divider()
            st.subheader("🔍 Search Consultation")
            
            col1, col2 = st.columns(2)
            with col1:
                disease_filter = st.text_input("Filter by Disease ID", placeholder="e.g., P1, P2, P3")
            with col2:
                method_filter = st.selectbox("Filter by Method", ["All", "FORWARD", "BACKWARD"])
            
            # Terapkan filter
            # FIX: Menggunakan 'conclusion' untuk filter
            search_results = [
                c for c in history 
                if (not disease_filter or c.get("diagnosis", {}).get("conclusion") == disease_filter) and
                   (method_filter == "All" or c.get("diagnosis", {}).get("method", "").upper() == method_filter)
            ]

            if disease_filter or method_filter != "All":
                st.info(f"🔎 Found **{len(search_results)}** consultation(s) matching criteria.")
                if search_results:
                    for result in search_results[:5]: # Tampilkan 5 hasil teratas
                        diag = result.get("diagnosis", {})
                        disease_id = diag.get("conclusion")
                        
                        # Dapatkan nama penyakit
                        disease_name = "N/A"
                        if disease_id and disease_id in db.diseases:
                            disease_name = db.diseases[disease_id].nama
                        elif diag.get("status") in ["FAILED", "INCONCLUSIVE", "REJECTED_SUGGESTION"]:
                            disease_name = diag.get("status").replace("_", " ").title()

                        timestamp = result.get("timestamp", "N/A")[:19].replace("T", " ")
                        cf = diag.get('cf', 0.0)

                        expander_title = f"**{disease_name}** (CF: {cf:.1%}) - {timestamp}"
                        
                        with st.expander(expander_title):
                            st.write(f"**Consultation ID:** `{result.get('consultation_id', 'N/A')}`")
                            
                            symptom_ids = result.get("symptoms", {}).get("ids", [])
                            symptom_names = []
                            for s_id in symptom_ids:
                                if s_id in db.symptoms:
                                    symptom_names.append(db.symptoms[s_id].name.replace("_", " ").title())
                                else:
                                    symptom_names.append(s_id)

                            st.write("**Gejala yang diberikan:**")
                            st.write(f"_{', '.join(symptom_names)}_")

                            st.divider()
                            
                            # Tampilkan kesimpulan dan aturan yang digunakan
                            st.write(f"**Kesimpulan Diagnosis:** {disease_name}")
                            
                            trace = diag.get("trace", [])
                            used_rules = sorted(list(set([step.get("rule_id") for step in trace if step.get("rule_id")])))
                            
                            if used_rules:
                                st.write(f"**Aturan yang Digunakan:** `{', '.join(used_rules)}`")
                            else:
                                st.write("**Aturan yang Digunakan:** Tidak ada aturan spesifik yang tercatat.")
            
        else:
            st.info("📭 Belum ada riwayat konsultasi. Jalankan diagnosis terlebih dahulu.")
    
    # ===== TAB 2: Statistics =====
    with tab2:
        st.subheader("📊 Statistik Sistem")
        
        # Storage statistics
        history_for_stats = storage.load_consultation_history(limit=None) # Load all for stats
        stats = storage.get_statistics(history_for_stats)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Total Consultations",
                value=stats.get("total_consultations", 0),
                delta=None
            )
        with col2:
            first_cons_ts = stats.get("first_consultation_timestamp")
            first_cons_val = "N/A"
            if first_cons_ts:
                first_cons_val = first_cons_ts[:10]
            st.metric(
                label="First Consultation",
                value=first_cons_val
            )
        with col3:
            last_cons_ts = stats.get("last_consultation_timestamp")
            last_cons_val = "N/A"
            if last_cons_ts:
                last_cons_val = last_cons_ts[:10]
            st.metric(
                label="Last Consultation",
                value=last_cons_val
            )
        
        st.divider()
        
        # Logger statistics
        st.subheader("📚 Knowledge Base Statistics")
        log_stats = logger.get_statistics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rules", log_stats.get("total_rules", 0))
        with col2:
            st.metric("Total Diseases", log_stats.get("total_diseases", 0))
        with col3:
            st.metric("Total Symptoms", log_stats.get("total_symptoms", 0))
        
        # Most used rules
        st.divider()
        st.subheader("🔥 Most Used Rules")
        
        top_n = st.slider("Top N rules", 3, 10, 5)
        top_rules = logger.get_most_used_rules(top_n=top_n)
        
        if top_rules:
            for i, rule_info in enumerate(top_rules, 1):
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.write(f"**#{i}**")
                with col2:
                    st.write(f"**Rule {rule_info['rule_id']}** → {rule_info['disease_name']}")
                with col3:
                    st.write(f"🔢 {rule_info['usage_count']} times")
        else:
            st.info("📊 Belum ada data penggunaan rules. Jalankan diagnosis untuk mulai tracking.")
    
    # ===== TAB 3: Export =====
    with tab3:
        st.subheader("📥 Export Data")
        
        st.write("Export riwayat konsultasi dan generate reports dalam berbagai format.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Export Consultation History to CSV**")
            st.caption("Export seluruh riwayat konsultasi ke format CSV")
            
            if st.button("📊 Generate CSV Export", width="stretch"):
                try:
                    csv_path = storage.export_to_csv()
                    st.success(f"✅ CSV exported: `{csv_path}`")
                    
                    # Download button
                    import os
                    if os.path.exists(csv_path):
                        with open(csv_path, 'r', encoding='utf-8') as f:
                            csv_data = f.read()
                            st.download_button(
                                label="⬇️ Download CSV",
                                data=csv_data,
                                file_name=f"consultations_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                width="stretch"
                            )
                except Exception as e:
                    st.error(f"❌ Error exporting CSV: {str(e)}")
        
        with col2:
            st.write("**📄 Generate Consultation Report**")
            st.caption("Generate detailed report dari konsultasi terakhir")
            
            # Get latest consultation
            history = storage.load_consultation_history(limit=1)
            
            if history:
                latest = history[0]
                # Langsung gunakan objek diagnosis dari history
                result = latest.get("diagnosis", {})
                
                st.info(f"Latest: **{result.get('conclusion', 'N/A')}** "
                       f"(CF: {result.get('cf', 0.0):.2%})")
                
                report_format = st.radio(
                    "Format:",
                    ["TXT", "PDF"],
                    horizontal=True,
                    label_visibility="collapsed"
                )
                
                if st.button(f"📄 Generate {report_format} Report", width="stretch"):
                    try:
                        symptom_ids = latest.get("symptoms", {}).get("ids", [])
                        user_cf = latest.get("user_cf", 0.8) # Gunakan 'user_cf'
                        
                        # Validasi bahwa 'result' tidak kosong
                        if not result or not result.get('conclusion'):
                            st.error("❌ Laporan tidak dapat dibuat karena diagnosis terakhir tidak berhasil.")
                        else:
                            if report_format == "TXT":
                                report_path = reporter.generate_txt_report(
                                    result=result,
                                    symptom_ids=symptom_ids,
                                    user_cf=user_cf
                                )
                                st.success(f"✅ TXT report saved: `{report_path}`")
                                
                                # Download button
                                with open(report_path, 'r', encoding='utf-8') as f:
                                    st.download_button(
                                        label="⬇️ Download TXT",
                                        data=f.read(),
                                        file_name=f"report_{result.get('conclusion', 'diagnosis')}.txt",
                                        mime="text/plain",
                                        width="stretch"
                                    )
                            
                            else:  # PDF
                                try:
                                    report_path = reporter.generate_pdf_report(
                                        result=result,
                                        symptom_ids=symptom_ids,
                                        user_cf=user_cf
                                    )
                                    st.success(f"✅ PDF report saved: `{report_path}`")
                                    
                                    with open(report_path, 'rb') as f:
                                        st.download_button(
                                            label="⬇️ Download PDF",
                                            data=f.read(),
                                            file_name=f"report_{result.get('conclusion', 'diagnosis')}.pdf",
                                            mime="application/pdf",
                                            width="stretch"
                                        )
                                except ImportError:
                                    st.error("❌ fpdf tidak terinstall. Install: `pip install fpdf`")
                        
                    except Exception as e:
                        st.error(f"❌ Error generating report: {str(e)}")
            else:
                st.warning("⚠️ Belum ada riwayat konsultasi. Jalankan diagnosis terlebih dahulu.")

if __name__ == "__main__":
    run()
