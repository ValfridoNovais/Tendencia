import pandas as pd
import streamlit as st
import altair as alt
from datetime import timedelta

# Carregar os dados
data_path = 'data/GDO_2024_2.csv'
data = pd.read_csv(data_path)
data['data_fato'] = pd.to_datetime(data['data_fato'])

# Definir o período dos últimos 84 dias a partir da data mais recente no dataset
end_date = data['data_fato'].max()
start_date = end_date - timedelta(days=83)

# Filtrar dados para o período de 84 dias
data_84_days = data[(data['data_fato'] >= start_date) & (data['data_fato'] <= end_date)]

# Sidebar para filtros
st.sidebar.header("Filtros")
companhias = data['cia_pm'].unique()
companhia_selecionada = st.sidebar.selectbox("Selecionar Companhia", options=["Todas"] + list(companhias))

# Filtrar por companhia, se necessário
if companhia_selecionada != "Todas":
    data_filtrada = data_84_days[data_84_days['cia_pm'] == companhia_selecionada]
else:
    data_filtrada = data_84_days

# Contagem diária de ocorrências
daily_counts = data_filtrada.groupby('data_fato').size().reindex(
    pd.date_range(start=start_date, end=end_date), fill_value=0
).reset_index()
daily_counts.columns = ['data', 'ocorrencias']

# Projeção de novas datas
st.sidebar.subheader("Projeção de Novas Datas")
dias_a_projetar = st.sidebar.slider("Dias a Projetar", 0, 28, 0)  # Inclui a opção de 0 dias para projeção
valor_projecao = int(st.sidebar.number_input("Valor Diário Projetado", value=int(daily_counts['ocorrencias'].mean())))

# Ajustar o número de dias reais mostrados no gráfico ao adicionar projeções
if dias_a_projetar > 0:
    # Remover os últimos `dias_a_projetar` dias reais para incluir projeções mantendo o total de 84 dias
    daily_counts_reduced = daily_counts.iloc[:-dias_a_projetar]

    # Criar DataFrame de projeções
    projecoes = pd.DataFrame({
        'data': pd.date_range(start=end_date + timedelta(days=1), periods=dias_a_projetar),
        'ocorrencias': [valor_projecao] * dias_a_projetar
    })

    # Concatenar os dados reduzidos com os dados de projeção
    daily_counts_with_projection = pd.concat([daily_counts_reduced, projecoes], ignore_index=True)
else:
    # Se `dias_a_projetar` for 0, usamos os dados reais sem projeção
    daily_counts_with_projection = daily_counts

# Recalcular métricas considerando os dias projetados, se houver
total_ocorrencias_84_dias = daily_counts_with_projection['ocorrencias'].sum()
media_longo_prazo = daily_counts_with_projection['ocorrencias'].mean()
media_curto_prazo = daily_counts_with_projection['ocorrencias'][-28:].mean()
comparacao_percentual = ((media_curto_prazo - media_longo_prazo) / media_longo_prazo) * 100

# Determinar a cor da linha de média de 28
if comparacao_percentual < -3:
    cor_media_28_dias = "green"
elif -3 <= comparacao_percentual <= 3:
    cor_media_28_dias = "yellow"
else:
    cor_media_28_dias = "red"

# Exibir cartõesmétricas
st.title("Dashboard de Ocorrências")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Ocorrências (84 dias)", total_ocorrencias_84_dias)
col2.metric("Média de Longo Prazo (84 dias)", f"{media_longo_prazo:.2f}")
col3.metric("Média de Curto Prazo (28 dias)", f"{media_curto_prazo:.2f}")
col4.metric("Comparação Percentual", f"{comparacao_percentual:.2f}%")

# Configuração do eixo x para garantir a visualização completa dos 84 dias e rótulos das datas
base_chart = alt.Chart(daily_counts_with_projection).encode(
    x=alt.X('data:T', title="Data", axis=alt.Axis(format="%d/%m", labelAngle=-45, tickCount=42, grid=True)),
    y=alt.Y('ocorrencias:Q', title="Contagem de Ocorrências"),
    tooltip=['data', 'ocorrencias']
)

# Gráfico de barras para as ocorrências diárias e projeções
bar_chart = base_chart.mark_bar().encode(
    y=alt.Y('ocorrencias:Q', title="Contagem de Ocorrências")
)

# Adicionar linha pontilhada para média de longo prazo (84 dias) com extensão dinâmica
line_chart = alt.Chart(pd.DataFrame({
    'data': daily_counts_with_projection['data'],
    'media_longo_prazo': [media_longo_prazo] * 84  # Estende a média de 84 dias para cobrir todo o gráfico
})).mark_line(strokeDash=[5, 5], color="black").encode(
    x='data:T',
    y='media_longo_prazo:Q',
    tooltip=alt.Tooltip('media_longo_prazo', format=".2f", title="Média 84 dias")
)

# Adicionar linha contínua para média de curto prazo (28 dias) com cor dinâmica
short_term_chart = alt.Chart(pd.DataFrame({
    'data': pd.date_range(end=end_date + timedelta(days=dias_a_projetar), periods=28),
    'media_curto_prazo': [media_curto_prazo] * 28
})).mark_line(color=cor_media_28_dias).encode(
    x='data:T',
    y='media_curto_prazo:Q',
    tooltip=alt.Tooltip('media_curto_prazo', format=".2f", title="Média 28 dias")
)

# Combinar o gráfico ajustado com a linha de médias cfr
st.altair_chart(bar_chart + line_chart + short_term_chart, use_container_width=True)
