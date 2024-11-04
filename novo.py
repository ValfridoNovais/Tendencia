import pandas as pd
import streamlit as st
import altair as alt
from datetime import timedelta

# Carregar os dados
data_path = 'data/GDO_2024_2.csv'
data = pd.read_csv(data_path)
data['data_fato'] = pd.to_datetime(data['data_fato'])

# Sidebar para filtros
st.sidebar.header("Filtros")

# Projeção de novas datas
st.sidebar.subheader("Projeção de Novas Datas")

# Contagem diária de ocorrências
daily_counts = data.groupby('data_fato').size().reindex(
    pd.date_range(start=start_date, end=end_date), fill_value=0
).reset_index()
daily_counts.columns = ['data', 'ocorrencias']

st.write("""
    # TÊNDENCIA DAS VÍTIMAS DE CRIMES CONTRA O PATRIMÔNIO
         Esta é uma análise das vítimas de crimes contra o patrimônio na área do 19º BPM.
    """)

print(data)# Gráfico de barras para as ocorrências diárias e projeções

bar_chart = base_chart.mark_bar().encode(
    y=alt.Y('ocorrencias:Q', title="Contagem de Ocorrências")
)