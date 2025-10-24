import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

def fish_selector():
    return st.multiselect(
        "Komoditas (opsional—untuk memfilter gejala/penyakit terkait)",
        ["Lele", "Nila", "Gurame"]
    )

def symptom_multiselect(symptoms: List[Dict[str, Any]], max_select: int = 10, default_ids: List[str] = None) -> List[str]:
    options = {s["name"]: s["id"] for s in symptoms}
    id_to_name = {s["id"]: s["name"] for s in symptoms}
    
    # Convert default IDs to names for multiselect
    default_names = []
    if default_ids:
        default_names = [id_to_name[sid] for sid in default_ids if sid in id_to_name]
    
    selected = st.multiselect(
        "Pilih gejala",
        options=list(options.keys()),
        default=default_names,
        help="Pilih beberapa gejala fisik/perilaku yang teramati."
    )
    if len(selected) > max_select:
        st.warning(f"Maksimal {max_select} gejala.")
        selected = selected[:max_select]
    return [options[name] for name in selected]

def confidence_slider(label: str = "Keyakinan pengguna (CF input)", default_value: float = 0.8):
    return st.slider(label, 0.0, 1.0, default_value, 0.05)

def result_card(conclusion: str, cf_value: float, recommendation: Optional[str] = None):
    st.success(f"**Hasil:** {conclusion}")
    st.write(f"**Confidence (CF):** {cf_value:.2f}")
    if recommendation:
        st.info(f"**Rekomendasi:** {recommendation}")

def prevention_tips(tips: Optional[list[str]] = None):
    if tips:
        st.markdown("**Pencegahan:**")
        for t in tips:
            st.write(f"- {t}")

def trace_expander(trace_rows: List[Dict[str, Any]]):
    if not trace_rows:
        return
    with st.expander("Lihat penjelasan (trace HOW)"):
        df = pd.DataFrame(trace_rows)
        st.dataframe(df, width="stretch")
