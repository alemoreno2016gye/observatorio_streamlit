from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.data_access import load_gold

st.title("Estructura y Drill-down")
structure = load_gold("kpi_structure")

metric = st.selectbox("Métrica", ["value_fob", "value_cif", "weight_tm"])
year = st.selectbox("Año", sorted(structure["year"].dropna().unique(), reverse=True))
current = structure[structure["year"] == year]

st.plotly_chart(
    px.sunburst(current, path=["sector", "hs2", "hs6"], values=metric, title="Composición Sector → HS2 → HS6"),
    use_container_width=True,
)
st.plotly_chart(px.treemap(current, path=["sector", "hs2"], values=metric, title="Treemap por sector/chapter"), use_container_width=True)
trend = current.groupby(["sector"], as_index=False)[metric].sum().sort_values(metric, ascending=False)
st.plotly_chart(px.bar(trend, x="sector", y=metric, title="Tendencia por sector"), use_container_width=True)

st.dataframe(current.sort_values(metric, ascending=False).head(200), use_container_width=True)
