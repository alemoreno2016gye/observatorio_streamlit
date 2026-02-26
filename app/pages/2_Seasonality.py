from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.data_access import load_gold

st.title("Estacionalidad")
season = load_gold("kpi_seasonality")
metric = st.selectbox("Métrica", ["value_fob", "value_cif", "weight_tm"])
sector = st.selectbox("Sector", ["Todos"] + sorted(season["sector"].dropna().unique().tolist()))

filtered = season.copy()
if sector != "Todos":
    filtered = filtered[filtered["sector"] == sector]

pivot = filtered.groupby(["year", "month"], as_index=False)[metric].sum()
heat = pivot.pivot(index="month", columns="year", values=metric).fillna(0)
fig = px.imshow(heat, title=f"Heatmap estacional - {metric}", aspect="auto", color_continuous_scale="Viridis")
st.plotly_chart(fig, use_container_width=True)
