import streamlit as st
from pathlib import Path
from ui.theming import page_header, pill
from ui.components import fish_selector, symptom_multiselect, confidence_slider, result_card, prevention_tips, trace_expander

# Backend contracts
from database.database_manager import DatabaseManager
from core.inference_engine import InferenceEngine

@st.cache_resource
def get_db():
    # Gunakan path absolute berdasarkan lokasi file ini
    current_file = Path(__file__).resolve()
    app_dir = current_file.parent.parent  # naik 2 level dari pages/
    db_path = app_dir / "database"
    
    db = DatabaseManager(db_path)
    db.load_all()
    return db

@st.cache_resource
def get_engine():
    return InferenceEngine()

def _symptoms_for_ui(db: DatabaseManager, fish_filter: list[str] | None = None):
    # asumsikan symptom punya optional field 'species' = ["Lele", "Nila", ...]
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

def run():
    page_header("Diagnosis", "Masukkan gejala lalu jalankan inferensi.")
    pill("Domain: Perikanan/Akuakultur • Ikan: Lele • Nila • Gurame")

    db = get_db()
    engine = get_engine()

    # Debug: Cek path database
    st.write(f"🔍 Debug - Database path: {db.database_path}")
    st.write(f"🔍 Debug - Database path exists: {db.database_path.exists()}")
    st.write(f"🔍 Debug - Symptoms file: {db.database_path / 'symptoms.json'}")
    st.write(f"🔍 Debug - Symptoms file exists: {(db.database_path / 'symptoms.json').exists()}")
    
    # Debug: Cek apakah symptoms berhasil dimuat
    st.write(f"🔍 Debug - Total symptoms loaded: {len(db.symptoms)}")
    
    if len(db.symptoms) > 0:
        st.write("🔍 Debug - Sample symptoms from db:")
        for i, (key, val) in enumerate(list(db.symptoms.items())[:3]):
            st.write(f"  - {key}: name={getattr(val, 'name', 'NO NAME')}, species={getattr(val, 'species', 'NO SPECIES')}")
    
    fish_filter = fish_selector()
    st.write(f"🔍 Debug - Fish filter selected: {fish_filter}")
    
    symptoms = _symptoms_for_ui(db, fish_filter)
    
    # Debug: Cek hasil filtering
    st.write(f"🔍 Debug - Symptoms after filter: {len(symptoms)}")
    if len(symptoms) > 0:
        st.write("🔍 Debug - First 3 symptoms for UI:", symptoms[:3])

    cols = st.columns([2, 1])
    with cols[0]:
        selected_symptom_ids = symptom_multiselect(symptoms, max_select=10)
    with cols[1]:
        user_cf = confidence_slider()

    st.divider()
    run_btn = st.button("🔎 Jalankan Diagnosis", type="primary", use_container_width=True, disabled=not selected_symptom_ids)

    if run_btn:
        with st.spinner("Menjalankan inferensi..."):
            result = engine.diagnose(
                symptom_ids=selected_symptom_ids,
                user_cf=user_cf,
                kb=db
            )

        if result and result.get("conclusion"):
            label = result.get("conclusion_label", result["conclusion"])
            result_card(label, result.get("cf", 0.0), result.get("recommendation"))
            prevention_tips(result.get("prevention"))
            trace_expander(result.get("trace", []))
        else:
            st.warning("Tidak ditemukan kesimpulan di atas ambang batas. Coba tambahkan gejala lain atau periksa kembali input.")

if __name__ == "__main__":
    run()
