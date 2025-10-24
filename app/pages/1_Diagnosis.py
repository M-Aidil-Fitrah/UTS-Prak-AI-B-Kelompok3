import streamlit as st
from pathlib import Path
from datetime import datetime
from ui.theming import page_header, pill
from ui.components import fish_selector, symptom_multiselect, confidence_slider, trace_expander

# Backend contracts
from database.database_manager import DatabaseManager
from core.inference_engine import InferenceEngine
from services.storage import StorageService
from services.logging_service import LoggingService
from services.reporting import ReportingService

# --- Backend Initialization ---
@st.cache_resource
def get_db():
    db_path = Path(__file__).parent.parent / "database"
    db = DatabaseManager(db_path)
    db.load_all()
    return db

@st.cache_resource
def get_engine():
    return InferenceEngine()

@st.cache_resource
def get_storage():
    return StorageService()

@st.cache_resource
def get_logger():
    return LoggingService()

@st.cache_resource
def get_reporter():
    return ReportingService(output_dir="reports")

# --- UI Helper Functions ---
def _symptoms_for_ui(db: DatabaseManager, fish_filter: list[str] | None = None):
    out = []
    for s in db.symptoms.values():
        species = getattr(s, "species", None)
        if fish_filter and species and not any(f in species for f in fish_filter):
            continue
        out.append({
            "id": s.id,
            "name": getattr(s, "name", s.id).replace("_", " ").title(),
            "description": getattr(s, "description", "")
        })
    return out

def save_current_diagnosis(storage: StorageService, logger: LoggingService):
    """Saves the current diagnosis result to history if it hasn't been saved yet."""
    if not st.session_state.get("result_saved", False):
        try:
            # Use a placeholder for the result if it's None (e.g., when showing alternatives)
            # This ensures the initial symptoms are still recorded.
            result_to_save = st.session_state.diagnosis_result
            if result_to_save is None:
                # Create a mock result for logging purposes when user rejects suggestions
                result_to_save = {
                    "status": "REJECTED_SUGGESTION",
                    "conclusion": None,
                    "cf": 0,
                    "trace": [],
                    "suggestions": st.session_state.alternatives_data
                }

            storage.save_consultation(
                symptom_ids=st.session_state.initial_symptoms,
                diagnosis_result=result_to_save,
                user_cf=st.session_state.user_cf
            )
            st.session_state.result_saved = True
            # Only log rules if there's a valid result with a trace
            if st.session_state.diagnosis_result:
                logger.log_diagnosis(
                    symptom_ids=st.session_state.initial_symptoms,
                    result=st.session_state.diagnosis_result
                )
        except Exception as e:
            st.error(f"Gagal menyimpan riwayat diagnosis: {e}")

def reset_diagnosis_state():
    """Resets all session state variables related to a diagnosis run."""
    st.session_state.diagnosis_result = None
    st.session_state.initial_symptoms = []
    st.session_state.show_alternatives = False
    st.session_state.alternatives_data = None
    st.session_state.user_cf = 0.8 # Reset to default
    st.session_state.result_saved = False # Reset save status
    st.session_state.questions_queue = [] # Reset antrian pertanyaan
    st.session_state.asked_symptoms = set() # Reset gejala yang sudah ditanya

# --- Main App Logic ---
def run():
    page_header("Diagnosis", "Masukkan gejala lalu jalankan inferensi.")
    pill("Domain: Perikanan/Akuakultur • Ikan: Lele • Nila • Gurame")

    # Get backend instances
    db = get_db()
    engine = get_engine()
    storage = get_storage()
    logger = get_logger()
    reporter = get_reporter()

    # Initialize session state
    if 'initial_symptoms' not in st.session_state:
        st.session_state.initial_symptoms = []
    if 'diagnosis_result' not in st.session_state:
        st.session_state.diagnosis_result = None
    if 'show_alternatives' not in st.session_state:
        st.session_state.show_alternatives = False
    if 'alternatives_data' not in st.session_state:
        st.session_state.alternatives_data = None
    if 'user_cf' not in st.session_state:
        st.session_state.user_cf = 0.8
    if 'questions_queue' not in st.session_state:
        st.session_state.questions_queue = []
    if 'asked_symptoms' not in st.session_state:
        st.session_state.asked_symptoms = set() # Lacak gejala yang sudah ditanya

    # --- Sidebar ---
    debug_mode = False
    with st.sidebar:
        st.caption(f"Rules: {len(db.rules)} | Diseases: {len(db.diseases)} | Symptoms: {len(db.symptoms)}")

    # --- Main UI ---
    # This section is now only for input, not for displaying results
    if not st.session_state.diagnosis_result and not st.session_state.show_alternatives:
        fish_filter = fish_selector()
        symptoms = _symptoms_for_ui(db, fish_filter)
        
        cols = st.columns([2, 1])
        with cols[0]:
            selected_symptom_ids = symptom_multiselect(symptoms, max_select=10, default_ids=st.session_state.initial_symptoms)
        with cols[1]:
            # Store user_cf in session state immediately
            st.session_state.user_cf = confidence_slider(default_value=st.session_state.user_cf)

        st.divider()
        
        if st.button("🔎 Jalankan Diagnosis", type="primary", width="stretch", disabled=not selected_symptom_ids):
            st.session_state.initial_symptoms = selected_symptom_ids
            with st.spinner("Menjalankan inferensi..."):
                result = engine.diagnose(symptom_ids=selected_symptom_ids, user_cf=st.session_state.user_cf, kb=db)
                st.session_state.diagnosis_result = result
                st.rerun()

    # --- Result Handling Block ---
    elif st.session_state.diagnosis_result:
        result = st.session_state.diagnosis_result
        status = result.get("status")
        
        # Display based on status
        if status == "SUCCESS":
            save_current_diagnosis(storage, logger)
            st.balloons()
            disease_id = result.get("conclusion")
            disease_info = result.get("disease_info", {})
            
            st.success(f"🎉 **Diagnosis Berhasil!**")
            st.write(f"**Penyakit:** {disease_info.get('nama', disease_id)}")
            st.write(f"**Confidence Factor:** {result.get('cf', 0):.1%}")
            
            if disease_info.get("pengobatan"):
                st.write("**💊 Pengobatan:**"); st.info(disease_info["pengobatan"])
            
            if disease_info.get("pencegahan"):
                with st.expander("🛡️ Pencegahan"):
                    st.write(disease_info["pencegahan"])

            # Menambahkan expander untuk jejak penalaran
            trace_expander(result)
            
            # Tombol untuk reset
            if st.button("🔄 Diagnosis Baru", width="stretch"):
                reset_diagnosis_state()
                st.rerun()

        elif status == "NEEDS_MORE_INFO":
            suggestions = result.get("suggestions", [])
            
            # Isi antrian jika kosong, dan pastikan tidak menanyakan gejala yang sama
            if not st.session_state.questions_queue and suggestions:
                all_missing = []
                for sug in suggestions:
                    for sid, sname in zip(sug['missing_symptom_ids'], sug['missing_symptom_names']):
                        if sid not in st.session_state.asked_symptoms:
                            # Simpan juga info penyakit terkait untuk konteks
                            all_missing.append({
                                "s_id": sid, 
                                "s_name": sname, 
                                "d_name": sug['disease_name'],
                                "d_percent": sug['percentage']
                            })
                # Hapus duplikat
                unique_missing = list({q['s_id']: q for q in all_missing}.values())
                st.session_state.questions_queue = unique_missing

            if st.session_state.questions_queue:
                # Ambil pertanyaan berikutnya dari antrian
                question = st.session_state.questions_queue[0]
                symptom_id_to_add = question['s_id']
                symptom_to_ask = question['s_name']
                
                st.info(f"💡 **Sistem mencurigai penyakit: {question['d_name']}** ({question['d_percent']:.0f}% cocok).")
                st.write(f"Untuk memastikannya, apakah ikan juga mengalami gejala berikut?")
                st.subheader(f"➡️ {symptom_to_ask}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Ya, Benar", use_container_width=True):
                        st.session_state.initial_symptoms.append(symptom_id_to_add)
                        st.session_state.asked_symptoms.add(symptom_id_to_add)
                        st.session_state.questions_queue = [] # Kosongkan antrian untuk evaluasi ulang
                        
                        with st.spinner("Menganalisis ulang dengan gejala baru..."):
                            new_result = engine.diagnose(
                                symptom_ids=st.session_state.initial_symptoms, 
                                user_cf=st.session_state.user_cf, 
                                kb=db
                            )
                            st.session_state.diagnosis_result = new_result
                            st.rerun()
                with col2:
                    if st.button("❌ Tidak, Gejala ini tidak ada", use_container_width=True):
                        st.session_state.asked_symptoms.add(symptom_id_to_add)
                        st.session_state.questions_queue.pop(0)
                        
                        if not st.session_state.questions_queue:
                            save_current_diagnosis(storage, logger)
                            st.session_state.show_alternatives = True
                            st.session_state.alternatives_data = suggestions
                            st.session_state.diagnosis_result = None
                        
                        st.rerun()
            else:
                # Jika tidak ada saran atau antrian habis, anggap inkonklusif
                save_current_diagnosis(storage, logger)
                st.warning("⚠️ Tidak ada gejala tambahan relevan yang bisa ditanyakan.")
                if st.button("🔄 Coba Lagi", use_container_width=True):
                    reset_diagnosis_state()
                    st.rerun()

        elif status == "INCONCLUSIVE":
            save_current_diagnosis(storage, logger)
            st.warning(f"⚠️ Tidak ditemukan diagnosis yang cukup yakin. CF tertinggi: {result.get('cf', 0.0):.1%}")
            st.info("💡 Coba tambahkan gejala lain atau tingkatkan tingkat keyakinan.")
            
            # Menambahkan expander untuk jejak penalaran
            trace_expander(result)

            if st.button("🔄 Coba Lagi", use_container_width=True):
                reset_diagnosis_state()
                st.rerun()

        elif status == "FAILED":
            save_current_diagnosis(storage, logger)
            st.error("❌ Tidak ada rules yang cocok dengan kombinasi gejala ini.")
            if st.button("🔄 Coba Lagi", width="stretch"):
                reset_diagnosis_state()
                st.rerun()

    # --- Alternatives Display Block ---
    elif st.session_state.show_alternatives:
        suggestions = st.session_state.alternatives_data
        st.warning("⚠️ Gejala tidak sesuai. Berikut adalah kemungkinan penyakit lainnya:")
        
        if suggestions and len(suggestions) > 1:
            for idx, sug in enumerate(suggestions[1:], 1):
                st.write(f"**{idx}. {sug['disease_name']}** ({sug['percentage']:.0f}% cocok)")
                st.write(f"   *Gejala dibutuhkan:* {', '.join(sug['missing_symptom_names'])}")
        else:
            st.info("💡 Tidak ada kemungkinan penyakit lain yang teridentifikasi.")

        if st.button("🔄 Diagnosis Baru", width="stretch"):
            reset_diagnosis_state()
            st.rerun()

if __name__ == "__main__":
    run()
