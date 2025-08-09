"""
Streamlit app: Calculadora de CDB IPCA+ com aportes mensais

O app permite:
- Informar aporte mensal, taxa anual (IPCA + spread), prazo em anos
- Escolher aporte no início ou no final do mês
- Gerar tabela mês-a-mês com: total investido, saldo bruto (se sacar naquele mês),
  rendimento bruto, IR (se sacar naquele mês) e saldo líquido
- Baixar os resultados em CSV

Observações sobre IR (tabela regressiva aplicada por contribuição):
- meses_investidos <= 6  -> 22.5%
- 7  <= meses_investidos <= 12 -> 20%
- 13 <= meses_investidos <= 24 -> 17.5%
- >24 -> 15%

Como funciona a simulação mensal:
- Para cada mês de saque t (1..n), o app calcula o futuro de cada aporte feito até t considerando
  quantos meses esse aporte ficou investido, calcula o lucro desse aporte,
  aplica a alíquota apropriada e soma tudo para gerar os valores agregados naquele mês t.

Execute: `streamlit run calculadora_cdb_ipca.py`
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date

st.set_page_config(page_title="Calculadora CDB IPCA+", layout="wide")

st.title("Calculadora de CDB IPCA+ (aportes mensais)")

with st.sidebar:
    st.header("Parâmetros")
    aporte_mensal = st.number_input("Aporte mensal (R$)", min_value=1.0, value=100.0, step=1.0, format="%.2f")
    taxa_anual = st.number_input("Taxa anual total (IPCA + spread) — % ao ano",
                                 min_value=0.0, value=12.0, step=0.1) / 100.0
    prazo_anos = st.number_input("Prazo (anos)", min_value=1, max_value=30, value=5)
    aporte_inicio = st.checkbox("Aporte no início do mês (senão: no final)", value=True)
    data_inicio = st.date_input("Data inicial do primeiro aporte", value=date.today())
    mostrar_grafico = st.checkbox("Mostrar gráfico", value=True)

# Parâmetros derivados
meses = int(prazo_anos * 12)
rm = (1 + taxa_anual) ** (1/12) - 1  # taxa mensal

st.markdown(f"**Resumo:** aporte R$ {aporte_mensal:.2f} por mês • taxa anual {(taxa_anual*100):.2f}% • "
            f"taxa mensal {(rm*100):.4f}% • prazo {prazo_anos} anos ({meses} meses)")

# Função para escolher aliquota IR pela quantidade de meses investidos
def aliquota_ir(meses_investidos: int) -> float:
    if meses_investidos <= 6:
        return 0.225
    elif meses_investidos <= 12:
        return 0.20
    elif meses_investidos <= 24:
        return 0.175
    else:
        return 0.15

# Gera datas dos aportes
if aporte_inicio:
    # aporte no início do mês
    aporte_dates = pd.date_range(start=data_inicio, periods=meses, freq='MS')
else:
    # aporte no final do mês
    aporte_dates = pd.date_range(start=data_inicio, periods=meses, freq='M')

# Simulação: para cada mês de saque t (1..meses) calcula o saldo se sacar naquele mês
rows = []
for t in range(1, meses + 1):
    total_investido = 0.0
    fv_total = 0.0
    lucro_total = 0.0
    ir_total = 0.0

    for m in range(0, t):
        meses_investidos = t - m
        aport = aporte_mensal
        fv = aport * ((1 + rm) ** meses_investidos)
        lucro = fv - aport
        ir_rate = aliquota_ir(meses_investidos)
        ir = lucro * ir_rate

        total_investido += aport
        fv_total += fv
        lucro_total += lucro
        ir_total += ir

    saldo_liquido = fv_total - ir_total
    data_saque = (aporte_dates[0] + pd.DateOffset(months=t-1)).date()

    rows.append({
        "Mês (t)": t,
        "Data do saque": data_saque,
        "Total Investido": round(total_investido, 2),
        "Saldo Bruto (se sacar)": round(fv_total, 2),
        "Rendimento Bruto": round(lucro_total, 2),
        "IR (se sacar)": round(ir_total, 2),
        "Saldo Líquido (se sacar)": round(saldo_liquido, 2)
    })

# Monta DataFrame
df = pd.DataFrame(rows)

st.subheader("Tabela mês a mês (se sacar naquele mês)")
st.dataframe(df.style.format({
    "Total Investido": "{:.2f}",
    "Saldo Bruto (se sacar)": "{:.2f}",
    "Rendimento Bruto": "{:.2f}",
    "IR (se sacar)": "{:.2f}",
    "Saldo Líquido (se sacar)": "{:.2f}"
}), height=400)

# Resumo final
final = df.iloc[-1]
st.subheader("Resumo final (após o prazo)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total investido", f"R$ {final['Total Investido']:.2f}")
col2.metric("Saldo bruto", f"R$ {final['Saldo Bruto (se sacar)']:.2f}")
col3.metric("IR estimado", f"R$ {final['IR (se sacar)']:.2f}")
col4.metric("Saldo líquido", f"R$ {final['Saldo Líquido (se sacar)']:.2f}")

# Plot
if mostrar_grafico:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df['Mês (t)'], df['Saldo Bruto (se sacar)'], label='Saldo Bruto (se sacar)')
    ax.plot(df['Mês (t)'], df['Saldo Líquido (se sacar)'], label='Saldo Líquido (se sacar)')
    ax.set_xlabel('Mês')
    ax.set_ylabel('R$')
    ax.set_title('Evolução do saldo (se sacar no mês)')
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

# Download CSV
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(label="Baixar CSV", data=csv,
                   file_name='simulacao_cdb_ipca.csv', mime='text/csv')

st.markdown("---")
st.markdown("**Observações:** este simulador aplica a tabela regressiva de IR por aporte individual, "
            "supondo que o imposto é cobrado quando você sacar o dinheiro. "
            "Se o seu produto descontar IR diferente, altere o método conforme necessário.")