from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.data_access import load_gold

st.set_page_config(page_title="Observatorio Ecuador–China", layout="wide")
st.title("Observatorio de Comercio Ecuador–China")

hist = load_gold("kpi_historical_series")
bal = load_gold("kpi_bilateral_balance")
rank = load_gold("kpi_country_ranking")

if hist.empty:
    st.warning("No gold data found. Run: `python -m etl.pipeline` first.")
    st.stop()

c1, c2, c3 = st.columns(3)
latest = hist.sort_values("period_date").iloc[-1]
c1.metric("Exportaciones FOB (último mes)", f"{latest['exports_fob']:,.0f}")
c2.metric("Importaciones CIF (último mes)", f"{latest['imports_cif']:,.0f}")
c3.metric("Ratio costo logístico", f"{latest['logistic_cost_ratio']:.2%}")

st.plotly_chart(px.line(hist, x="period_date", y=["exports_fob", "imports_fob", "imports_cif"], title="Serie histórica"), use_container_width=True)
st.plotly_chart(px.bar(bal, x="year", y="trade_balance_fob", title="Balance bilateral Ecuador–China (FOB)"), use_container_width=True)

top5 = rank[rank["ranking"] <= 5]
st.plotly_chart(
    px.bar(top5, x="country_name", y="value_fob", color="flow", animation_frame="year", title="Top 5 socios por año"),
    use_container_width=True,
)
