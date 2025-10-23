import streamlit as st

PRIMARY = "var(--primary-color, #0ea5e9)"  # cyan-500 fallback
MUTED = "#64748b"  # slate-500

def page_header(title: str, subtitle: str | None = None):
    st.markdown(f"<h2 style='margin-bottom:0.2rem'>{title}</h2>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<p style='color:{MUTED};margin-top:0'>{subtitle}</p>", unsafe_allow_html=True)

def pill(text: str):
    st.markdown(
        f"""
        <span style="
          padding:4px 10px;border-radius:9999px;
          background:rgba(14,165,233,0.12);color:#0ea5e9;
          font-size:0.85rem;">{text}</span>
        """,
        unsafe_allow_html=True
    )
