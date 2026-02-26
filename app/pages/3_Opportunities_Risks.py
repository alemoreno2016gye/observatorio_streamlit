from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.data_access import load_gold

st.title("Oportunidades y Riesgos")
emerging = load_gold("kpi_emerging_products")
dep = load_gold("kpi_china_dependency")
china_share = load_gold("kpi_ecuador_in_china")

selected_year = st.selectbox("Año", sorted(emerging["year"].dropna().unique(), reverse=True))

em_current = emerging[emerging["year"] == selected_year].sort_values("emerging_score", ascending=False).head(30)
st.subheader("Índice de productos emergentes")
st.plotly_chart(px.bar(em_current, x="hs10", y="emerging_score", title="Top productos emergentes"), use_container_width=True)

st.subheader("Dependencia con China")
dep_y = dep[dep["year"] == selected_year]
st.plotly_chart(px.histogram(dep_y, x="china_share", nbins=20, title="Distribución de dependencia por HS2"), use_container_width=True)

st.subheader("Participación de Ecuador en importaciones de China")
cs_y = china_share[china_share["year"] == selected_year].sort_values("ecuador_share", ascending=False).head(30)
st.plotly_chart(px.bar(cs_y, x="hs2", y="ecuador_share", title="Market share Ecuador por HS2"), use_container_width=True)
st.dataframe(cs_y, use_container_width=True)
