import streamlit as st
from pathlib import Path
from ui.theming import page_header
from database.database_manager import DatabaseManager
import pandas as pd

@st.cache_resource
def get_db():
    db = DatabaseManager(Path("database"))
    db.load_all()
    return db

def run():
    page_header("KB Explorer", "Jelajahi gejala, penyakit, dan aturan.")
    db = get_db()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Gejala")
        s_df = pd.DataFrame([s.model_dump() for s in db.symptoms.values()])
        st.dataframe(s_df, use_container_width=True, height=420)

    with col2:
        st.subheader("Penyakit")
        d_df = pd.DataFrame([d.model_dump() for d in db.diseases.values()])
        st.dataframe(d_df, use_container_width=True, height=420)

    with col3:
        st.subheader("Rules")
        r_df = pd.DataFrame([{"id": rid, **r.model_dump()} for rid, r in db.rules.items()])
        st.dataframe(r_df, use_container_width=True, height=420)

if __name__ == "__main__":
    run()
