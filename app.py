"""房产估值工具 — 导航入口

三个模型（DCF + Hedonic + 提前还贷）集成在一个 Streamlit 多页面应用。
"""
import streamlit as st

st.set_page_config(page_title="房产估值工具", layout="wide")

home = st.Page("pages/home.py", title="房产估值", icon="🏠", default=True)
hedonic = st.Page("pages/1_hedonic.py", title="房源调整", icon="📐")
prepay = st.Page("pages/2_prepayment.py", title="提前还贷", icon="💰")
methodology = st.Page("pages/3_methodology.py", title="计算依据", icon="📖")

pg = st.navigation([home, hedonic, prepay, methodology])
pg.run()
