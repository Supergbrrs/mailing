import streamlit as st

hide_streamlit_style = """
    <style>
    /* Esconder menu hamburguer */
    #MainMenu {visibility: hidden;}
    /* Esconder rodapé */
    footer {visibility: hidden;}
    /* Esconder ícone GitHub (normalmente dentro de header) */
    header > div:nth-child(1) {visibility: hidden;}
    </style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)


import streamlit as st
import pandas as pd
import re
import os
import requests

# Função para baixar blacklist do Google Drive (cache local)
@st.cache_data(show_spinner=False)
def carregar_blacklist_google_drive(google_drive_id):
    local_path = "blacklist.csv"
    if not os.path.exists(local_path):
        url = f"https://drive.google.com/uc?export=download&id={google_drive_id}"
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(response.content)
        else:
            st.error("Erro ao baixar blacklist do Google Drive.")
            return None
    try:
        blacklist = pd.read_csv(local_path, header=None, names=['Numero'], dtype=str)
        return blacklist
    except Exception as e:
        st.error(f"Erro ao ler blacklist: {e}")
        return None

# (Mantém as outras funções do seu código)

# Função para carregar arquivos
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
        return df
    return None

def ajustar_colunas(df):
    if df.shape[1] == 1:
        df = df.iloc[:, 0].str.split(';', expand=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
    return df

def validar_numero(numero):
    numero = str(numero).strip()
    numero = re.sub(r'\D', '', numero)

    if numero.startswith("55") and len(numero) > 10:
        numero = numero[2:]

    if len(numero) < 10 or len(numero) > 11:
        return "Inválido"

    if not numero.startswith(("2", "3", "4", "5", "6", "7", "8", "9")):
        return "Inválido"

    return "Válido"

# Interface Streamlit
st.title("Sistema de Higienização de Mailing 📞")

uploaded_file = st.file_uploader("Carregue seu arquivo de mailing (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    df = carregar_arquivo(uploaded_file)

    if df is not None:
        st.write("📜 **Visualização dos dados do mailing:**")
        st.dataframe(df.head())

        colunas_telefone = [col for col in df.columns if col.startswith("tel")]
        colunas_destino = [col for col in df.columns if col.startswith("des")]

        if not colunas_telefone and not colunas_destino:
            st.error("⚠️ Nenhuma coluna de telefone ou destino encontrada! Verifique o arquivo.")
        else:
            st.success(f"📌 Colunas identificadas: Telefones → {colunas_telefone}, Destinos → {colunas_destino}")

            # Insira aqui o ID do arquivo no Google Drive da sua blacklist
            google_drive_id = "1kEHYl6VOyAFuBpn7rmpbHXqSw_w774ua"

            blacklist = carregar_blacklist_google_drive(google_drive_id)

            if blacklist is not None:
                blacklist_set = set(blacklist["Numero"].astype(str).values)  # para busca rápida

                for coluna in colunas_telefone + colunas_destino:
                    df[coluna] = df[coluna].astype(str)

                    # Remove números na blacklist
                    df[coluna] = df[coluna].apply(lambda x: "" if x in blacklist_set else x)

                    # Opcional: validar números (se quiser, use ou remova)
                    # df[f"Status_{coluna}"] = df[coluna].apply(validar_numero)

            # Exibir estatísticas (se quiser)
            total_validos = 0
            total_invalidos = 0
            for coluna in colunas_telefone + colunas_destino:
                validos = df[coluna].apply(validar_numero) == "Válido"
                total_validos += validos.sum()
                total_invalidos += (~validos).sum()

            st.write("📊 **Resumo Estatístico:**")
            st.write(f"✅ Números válidos após higienização: **{total_validos}**")
            st.write(f"❌ Números inválidos após higienização: **{total_invalidos}**")

            st.write("📜 **Visualização final do arquivo:**")
            st.dataframe(df)

            # Download em Excel
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="💾 Baixar mailing higienizado (.xlsx)",
                data=buffer.getvalue(),
                file_name="mailing_higienizado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
