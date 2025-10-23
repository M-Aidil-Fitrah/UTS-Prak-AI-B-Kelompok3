import streamlit as st
from pathlib import Path
import yaml

CONFIG_PATH = Path("configs/app.yaml")

@st.cache_resource
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "app": {"name": "Sistem Pakar Ikan Air Tawar – Kelompok 3", "theme": "dark"},
        "inference": {"mode": "forward", "min_confidence": 0.6},
        "database": {"path": "database/", "auto_reload": True},
        "ui": {"show_trace": True, "max_symptoms_selectable": 10}
    }

CONFIG = load_config()

st.set_page_config(
    page_title=CONFIG["app"]["name"],
    page_icon="🐟",
    layout="wide"
)

st.sidebar.title("🐟 " + CONFIG["app"]["name"])
st.sidebar.caption("Frontend GUI – Streamlit")

st.sidebar.markdown("### Navigasi")
st.sidebar.page_link("pages/1_Diagnosis.py", label="Diagnosis")
st.sidebar.page_link("pages/2_Knowledge_Acquisition.py", label="Knowledge Acquisition")
st.sidebar.page_link("pages/3_History_&_Reports.py", label="History & Reports")
st.sidebar.page_link("pages/4_KB_Explorer.py", label="KB Explorer")

st.sidebar.divider()
with st.sidebar.expander("Konfigurasi Ringkas"):
    st.write(f"Mode inferensi: **{CONFIG['inference']['mode']}**")
    st.write(f"Threshold CF: **{CONFIG['inference']['min_confidence']}**")
    st.write(f"DB Path: `{CONFIG['database']['path']}`")

st.title("Sistem Pakar Penyakit Ikan Air Tawar")
st.markdown(
    """
    **Studi kasus**: Lele, Nila, Gurame.  
    Masukkan gejala fisik (mis. **bintik putih, luka, insang pucat**) dan perilaku (mis. **berenang tidak normal, nafsu makan turun**).  
    Sistem akan menalar dan menampilkan **nama penyakit**, **tingkat keyakinan (CF)**, serta **saran pengobatan & pencegahan**.
    """
)
