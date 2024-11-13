import pandas as pd
import streamlit as st
import altair as alt
from datetime import timedelta

# Sidebar para upload de arquivo
st.sidebar.header("Upload de Arquivo")
uploaded_file = st.sidebar.file_uploader("Escolha o arquivo CSV", type="csv")

# Continuação do processamento se um arquivo for carregado
if uploaded_file:
    # Carregar os dados com parsing adequado e ajustes nas colunas
    data = pd.read_csv(uploaded_file, delimiter=';', on_bad_lines='skip')
    data['DATA_FATO'] = pd.to_datetime(data['DATA_FATO'], format='%d/%m/%Y', errors='coerce')
    
    # Filtrar linhas com datas válidas
    data = data.dropna(subset=['DATA_FATO'])

    # Definir o intervalo de data para os últimos 84 dias
    end_date = data['DATA_FATO'].max()
    start_date = end_date - timedelta(days=83)
    
    # Filtrar dados dos últimos 84 dias
    data_84_days = data[(data['DATA_FATO'] >= start_date) & (data['DATA_FATO'] <= end_date)]

    # Preencher dias faltantes com ICCP_TOTAL = 0 nos últimos 84 dias
    date_range = pd.date_range(start=start_date, end=end_date)
    data_84_days = data_84_days.drop_duplicates(subset=['DATA_FATO'])
    data_84_days_complete = data_84_days.set_index('DATA_FATO').reindex(date_range, fill_value=0).rename_axis('DATA_FATO').reset_index()
    
    # Ordenar os valores para calcular a mediana
    sorted_values = data_84_days_complete['ICCP_TOTAL'].sort_values().reset_index(drop=True)

    # Calcular o limite inferior (7º valor) e superior (25º valor) com base no exemplo dado
    lower_limit_value = sorted_values.iloc[20]  # 7º valor
    upper_limit_value = sorted_values.iloc[63]  # 25º valor
    
    # Calcular a diferença e aplicar a constante de 1.5 para o limite superior
    difference = upper_limit_value - lower_limit_value
    upper_limit_final = upper_limit_value + (difference * 1.5)

    # Ajustar valores no ICCP_TOTAL ao limite superior calculado
    data['ICCP_TOTAL_ADJUSTED'] = data['ICCP_TOTAL'].apply(lambda x: min(x, upper_limit_final))

    # Recalcular métricas usando o ICCP_TOTAL ajustado
    data_84_days_complete['ICCP_TOTAL_ADJUSTED'] = data['ICCP_TOTAL_ADJUSTED']

    # Filtros da Sidebar
    st.sidebar.header("Filtros")
    companhias = data['UNID_AREA_NIVEL_6'].unique()
    companhia_selecionada = st.sidebar.selectbox("Selecionar Companhia", options=["Todas"] + list(companhias))

    # Filtrar por companhia selecionada se necessário
    if companhia_selecionada != "Todas":
        data_filtrada = data_84_days_complete[data_84_days_complete['UNID_AREA_NIVEL_6'] == companhia_selecionada]
    else:
        data_filtrada = data_84_days_complete

    # Somar ICCP_TOTAL ajustado por data
    daily_counts = data_filtrada.groupby('DATA_FATO')['ICCP_TOTAL_ADJUSTED'].sum().reindex(
        pd.date_range(start=start_date, end=end_date), fill_value=0
    ).reset_index()
    daily_counts.columns = ['data', 'ocorrencias']

    # Opções de projeção da sidebar
    st.sidebar.subheader("Projeção de Novas Datas")
    dias_a_projetar = st.sidebar.slider("Dias a Projetar", 0, 28, 0)
    valor_projecao = int(st.sidebar.number_input("Valor Diário Projetado", value=int(daily_counts['ocorrencias'].mean())))

    # Ajustar dias reais exibidos no gráfico com projeções
    if dias_a_projetar > 0:
        daily_counts_reduced = daily_counts.iloc[:-dias_a_projetar]
        projecoes = pd.DataFrame({
            'data': pd.date_range(start=end_date + timedelta(days=1), periods=dias_a_projetar),
            'ocorrencias': [valor_projecao] * dias_a_projetar
        })
        daily_counts_with_projection = pd.concat([daily_counts_reduced, projecoes], ignore_index=True)
    else:
        daily_counts_with_projection = daily_counts

    # Calcular métricas com projeções se disponíveis
    total_ocorrencias_84_dias = daily_counts_with_projection['ocorrencias'].sum()
    media_longo_prazo = daily_counts_with_projection['ocorrencias'].mean()
    media_curto_prazo = daily_counts_with_projection['ocorrencias'][-28:].mean()
    comparacao_percentual = ((media_curto_prazo - media_longo_prazo) / media_longo_prazo) * 100

    # Determinar a cor da linha de média de 28 dias
    if comparacao_percentual < -3:
        cor_media_28_dias = "green"
    elif -3 <= comparacao_percentual <= 3:
        cor_media_28_dias = "yellow"
    else:
        cor_media_28_dias = "red"

    # Exibir métricas
    st.title("Dashboard de Ocorrências")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Ocorrências (84 dias)", total_ocorrencias_84_dias)
    col2.metric("Média de Longo Prazo (84 dias)", f"{media_longo_prazo:.2f}")
    col3.metric("Média de Curto Prazo (28 dias)", f"{media_curto_prazo:.2f}")
    col4.metric("Comparação Percentual", f"{comparacao_percentual:.2f}%")

    # Gráfico de barras para ocorrências diárias e projeções
    base_chart = alt.Chart(daily_counts_with_projection).encode(
        x=alt.X('data:T', title="Data", axis=alt.Axis(format="%d/%m", labelAngle=-45, tickCount=42, grid=True)),
        y=alt.Y('ocorrencias:Q', title="Contagem de Ocorrências"),
        tooltip=['data', 'ocorrencias']
    )

    bar_chart = base_chart.mark_bar()
    
    # Linha para o limite superior calculado
    upper_limit_line = alt.Chart(pd.DataFrame({
        'data': daily_counts_with_projection['data'],
        'upper_limit': [upper_limit_final] * len(daily_counts_with_projection['data'])
    })).mark_line(strokeDash=[3, 3], color="lightblue").encode(
        x='data:T',
        y='upper_limit:Q',
        tooltip=alt.Tooltip('upper_limit', format=".2f", title="Limite Superior")
    )

    # Combine todos os gráficos
    st.altair_chart(upper_limit_line + bar_chart, use_container_width=True)

else:
    st.warning("Por favor, faça o upload de um arquivo CSV para continuar.")
