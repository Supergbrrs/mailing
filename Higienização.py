import streamlit as st
import pandas as pd
import re
import requests
from io import BytesIO

# Função para carregar arquivos
@st.cache_data(show_spinner=False)
def carregar_arquivo(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None, dtype=str)
            if df.shape[1] == 1:
                df = df.iloc[:, 0].str.split(';', expand=True)
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, dtype=str)
        else:
            st.error("Formato de arquivo não suportado! Envie um CSV ou XLSX.")
            return None

        df.columns = df.columns.fillna('')
        novas_colunas = []
        vazio_count = 1
        col_renomeadas = False
        for col in df.columns:
            if col == '' or col.lower() == 'vazio':
                novas_colunas.append(f'vazio{vazio_count}')
                vazio_count += 1
                col_renomeadas = True
            else:
                novas_colunas.append(col)
        df.columns = novas_colunas

        if col_renomeadas:
            st.warning("Colunas vazias foram renomeadas para vazio1, vazio2, etc.")

        return df
    return None

# Função para carregar blacklist do Google Drive
@st.cache_data(show_spinner=False)
def carregar_blacklist():
    try:
        url = "https://drive.google.com/uc?id=1fMLO1ev3Hev1xANyspv2qIHpLFqvFzU2"
        file_content = requests.get(url).content
        df_blacklist = pd.read_csv(BytesIO(file_content), header=None, names=['Numero'], dtype=str)
        df_blacklist['Numero'] = df_blacklist['Numero'].str.replace(r'\D', '', regex=True)
        return df_blacklist
    except Exception as e:
        st.error(f"Erro ao carregar a blacklist: {e}")
        return None

# Função para validar número
def validar_numero(numero):
    numero = str(numero).strip()
    numero = re.sub(r'\D', '', numero)

    if numero.startswith("55") and len(numero) > 10:
        numero = numero[2:]

    if len(numero) < 10 or len(numero) > 11:
        return "Inválido"

    if not numero.startswith(tuple("23456789")):
        return "Inválido"

    return "Válido"

# App Streamlit
st.set_page_config(page_title="Higienização de Mailing", layout="centered")
st.title("📞 Sistema de Higienização de Mailing")

uploaded_file = st.file_uploader("Carregue seu arquivo de mailing (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    df = carregar_arquivo(uploaded_file)

    if df is not None:
        st.write("📜 Pré-visualização dos dados:")
        st.dataframe(df.head())

        colunas_telefone = [col for col in df.columns if col.lower().startswith("tel") or col.lower().startswith("des")]

        if not colunas_telefone:
            st.error("⚠️ Nenhuma coluna de telefone ou destino encontrada!")
        else:
            st.success(f"🔍 Colunas encontradas para validação e blacklist: {colunas_telefone}")

            blacklist = carregar_blacklist()

            if blacklist is not None:
                numeros_blacklist = set(blacklist['Numero'].astype(str))

                for col in colunas_telefone:
                    df[col] = df[col].astype(str).str.replace(r'\D', '', regex=True)
                    df[col] = df[col].apply(lambda x: '' if x in numeros_blacklist else x)

                # 🚨 NOVO: remover números inválidos
                for col in colunas_telefone:
                    df[col] = df[col].apply(lambda x: x if validar_numero(x) == "Válido" else '')

                total_validos = 0
                total_invalidos = 0

                for col in colunas_telefone:
                    valids = df[col].apply(validar_numero)
                    total_validos += (valids == "Válido").sum()
                    total_invalidos += (valids == "Inválido").sum()

                st.write("📊 **Resumo Estatístico:**")
                st.write(f"✅ Números válidos após higienização: **{total_validos}**")
                st.write(f"❌ Números inválidos após higienização: **{total_invalidos}**")

                st.write("📥 Baixar arquivo higienizado:")
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Higienizado')

                st.download_button(
                    label="💾 Baixar XLSX",
                    data=buffer.getvalue(),
                    file_name="mailing_higienizado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
