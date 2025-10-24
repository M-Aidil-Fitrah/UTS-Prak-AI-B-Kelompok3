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
        
        if st.button("🔎 Jalankan Diagnosis", type="primary", use_container_width=True, disabled=not selected_symptom_ids):
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
            
            # Tombol untuk reset
            if st.button("🔄 Diagnosis Baru", use_container_width=True):
                reset_diagnosis_state()
                st.rerun()

        elif status == "NEEDS_MORE_INFO":
            st.info("💡 **Sistem menemukan kemungkinan penyakit yang hampir cocok. Mari periksa gejala tambahan:**")
            suggestions = result.get("suggestions", [])
            if suggestions:
                top_suggestion = suggestions[0]
                symptom_to_ask = top_suggestion['missing_symptom_names'][0]
                symptom_id_to_add = top_suggestion['missing_symptom_ids'][0]

                st.write(f"**Kemungkinan penyakit:** {top_suggestion['disease_name']} ({top_suggestion['percentage']:.0f}% cocok)")
                st.write(f"**Apakah ikan mengalami: {symptom_to_ask}?**")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Ya", use_container_width=True):
                        new_symptoms = st.session_state.initial_symptoms + [symptom_id_to_add]
                        st.session_state.initial_symptoms = new_symptoms
                        
                        # Trigger re-diagnosis
                        with st.spinner("Menjalankan diagnosis ulang..."):
                            new_result = engine.diagnose(symptom_ids=new_symptoms, user_cf=st.session_state.user_cf, kb=db)
                            st.session_state.diagnosis_result = new_result
                            st.rerun()
                with col2:
                    if st.button("❌ Tidak", use_container_width=True):
                        # Save before showing alternatives
                        save_current_diagnosis(storage, logger)
                        st.session_state.show_alternatives = True
                        st.session_state.alternatives_data = suggestions
                        st.session_state.diagnosis_result = None # Clear result to show alternatives
                        st.rerun()

        elif status == "INCONCLUSIVE":
            save_current_diagnosis(storage, logger)
            st.warning(f"⚠️ Tidak ditemukan diagnosis yang cukup yakin. CF tertinggi: {result.get('cf', 0.0):.1%}")
            st.info("💡 Coba tambahkan gejala lain atau tingkatkan tingkat keyakinan.")
            if st.button("🔄 Coba Lagi", use_container_width=True):
                reset_diagnosis_state()
                st.rerun()

        elif status == "FAILED":
            save_current_diagnosis(storage, logger)
            st.error("❌ Tidak ada rules yang cocok dengan kombinasi gejala ini.")
            if st.button("🔄 Coba Lagi", use_container_width=True):
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

        if st.button("🔄 Diagnosis Baru", use_container_width=True):
            reset_diagnosis_state()
            st.rerun()

if __name__ == "__main__":
    run()
