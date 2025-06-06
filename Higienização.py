import streamlit as st
import pandas as pd
import re
from collections import Counter
from io import BytesIO

# Corrige colunas duplicadas automaticamente
def corrigir_colunas_duplicadas(colunas):
    contador = Counter()
    novas_colunas = []
    for col in colunas:
        contador[col] += 1
        if contador[col] > 1:
            novas_colunas.append(f"{col}_{contador[col]}")
        else:
            novas_colunas.append(col)
    return novas_colunas

# Carrega o arquivo enviado (CSV ou XLSX)
def carregar_arquivo(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)
            df = ajustar_colunas(df)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado! Envie um CSV ou XLSX.")
            return None

        colunas_antes = list(df.columns)
        df.columns = corrigir_colunas_duplicadas(df.columns)
        if colunas_antes != list(df.columns):
            st.warning("⚠️ Havia colunas com nomes duplicados. Elas foram renomeadas automaticamente.")
        return df
    return None

# Ajusta colunas separadas por ponto e vírgula
def ajustar_colunas(df):
    if df.shape[1] == 1:
        df = df.iloc[:, 0].str.split(';', expand=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
    return df

# Carrega blacklist como set (rápido)
def carregar_blacklist():
    try:
        blacklist = pd.read_csv("blacklist.csv", header=None, names=['Numero'], usecols=[0])
        blacklist.drop_duplicates(inplace=True)
        return set(blacklist["Numero"].astype(str))
    except Exception as e:
        st.error(f"Erro ao carregar a blacklist: {e}")
        return None

# Validação simples (retorna True/False)
def validar_numero(numero):
    numero = str(numero).strip()
    numero = re.sub(r'\D', '', numero)
    if numero.startswith("55"):
        numero = numero[2:]
    return bool(re.fullmatch(r'[1-9]\d{9,10}', numero))

# Interface do app
st.title("📞 Sistema de Higienização de Mailing")

uploaded_file = st.file_uploader("Carregue seu arquivo de mailing (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    df = carregar_arquivo(uploaded_file)

    if df is not None:
        st.write("📜 **Prévia dos dados carregados:**")
        st.dataframe(df.head())

        colunas_telefone = [col for col in df.columns if col.lower().startswith("tel")]
        colunas_destino = [col for col in df.columns if col.lower().startswith("des")]

        if not colunas_telefone and not colunas_destino:
            st.error("⚠️ Nenhuma coluna de telefone ou destino encontrada! Verifique o arquivo.")
        else:
            st.success(f"📌 Colunas identificadas: Telefones → {colunas_telefone}, Destinos → {colunas_destino}")
            
            blacklist_set = carregar_blacklist()
            if blacklist_set is not None:
                colunas_alvo = colunas_telefone + colunas_destino

                total_validos = 0
                total_invalidos = 0

                for coluna in colunas_alvo:
                    df[coluna] = df[coluna].astype(str)
                    df[coluna] = df[coluna].str.replace(r'\D', '', regex=True)
                    df[coluna] = df[coluna].str.replace(r'^55', '', regex=True)
                    df[coluna] = df[coluna].where(~df[coluna].isin(blacklist_set), "")

                    # Contar válidos/invalidos sem alterar o DataFrame
                    valid_flags = df[coluna].apply(validar_numero)
                    total_validos += valid_flags.sum()
                    total_invalidos += (~valid_flags).sum()

                st.write("📊 **Resumo da Higienização:**")
                st.write(f"✅ Válidos: **{total_validos}**")
                st.write(f"❌ Inválidos: **{total_invalidos}**")

                st.write("📄 **Mailing higienizado:**")
                st.dataframe(df)

                # Gera arquivo Excel na memória
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Higienizado')
                    
                buffer.seek(0)

                st.download_button(
                    label="💾 Baixar arquivo higienizado (.xlsx)",
                    data=buffer,
                    file_name="mailing_higienizado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
