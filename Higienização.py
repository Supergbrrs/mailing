import streamlit as st
import pandas as pd
import re
import requests
from io import BytesIO

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Higienização de Mailing", layout="wide")

# --- CARREGAR BLACKLIST DO GOOGLE DRIVE ---
@st.cache_data(show_spinner="🔄 Baixando blacklist...")
def carregar_blacklist():
    try:
        url = "https://drive.google.com/uc?export=download&id=1kEHYl6VOyAFuBpn7rmpbHXqSw_w774ua"  # substitua pelo seu ID
        response = requests.get(url)
        blacklist = pd.read_csv(BytesIO(response.content), header=None, names=["Numero"])
        blacklist["Numero"] = blacklist["Numero"].astype(str).str.strip()
        return blacklist
    except Exception as e:
        st.error(f"Erro ao carregar a blacklist: {e}")
        return None

# --- AJUSTE DE COLUNAS VAZIAS OU DUPLICADAS ---
def renomear_colunas_vazias_e_duplicadas(cols):
    seen = {}
    vazio_count = 1
    new_cols = []

    for col in cols:
        if pd.isna(col) or str(col).strip() == '':
            col = f'vazio{vazio_count}'
            vazio_count += 1

        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 0

        new_cols.append(col)
    
    return new_cols

# --- VALIDAÇÃO DE NÚMERO ---
def validar_numero(numero):
    numero = str(numero).strip()
    numero = re.sub(r'\D', '', numero)

    if numero.startswith("55") and len(numero) > 10:
        numero = numero[2:]

    if len(numero) < 10 or len(numero) > 11:
        return False

    if not numero.startswith(("2", "3", "4", "5", "6", "7", "8", "9")):
        return False

    return True

# --- HIGIENIZAÇÃO DE DADOS ---
def higienizar(df, blacklist, colunas_telefone):
    for col in colunas_telefone:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].apply(lambda x: "" if not validar_numero(x) or x in blacklist["Numero"].values else x)
    return df

# --- INTERFACE STREAMLIT ---
st.title("📞 Higienização de Mailing")

uploaded_file = st.file_uploader("📂 Envie seu arquivo de mailing (.csv ou .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Renomear colunas se necessário
        novas_colunas = renomear_colunas_vazias_e_duplicadas(df.columns)
        if df.columns.tolist() != novas_colunas:
            st.warning("⚠️ Algumas colunas foram renomeadas (ex: 'vazio1', 'vazio2') para evitar erros.")
            df.columns = novas_colunas

        st.subheader("👁️ Prévia dos dados:")
        st.dataframe(df.head())

        # Identificar colunas com telefone
        colunas_telefone = [col for col in df.columns if col.lower().startswith("tel") or col.lower().startswith("des")]

        if not colunas_telefone:
            st.error("❌ Nenhuma coluna de telefone encontrada (ex: 'tel1', 'des1')!")
        else:
            st.success(f"📌 Colunas identificadas: {colunas_telefone}")

            # Carregar blacklist
            blacklist = carregar_blacklist()
            if blacklist is not None:
                df = higienizar(df, blacklist, colunas_telefone)

                # Exibir resultado
                st.subheader("📊 Estatísticas:")
                total = sum(df[col].astype(str).str.strip().ne('').sum() for col in colunas_telefone)
                st.write(f"✅ Telefones válidos após higienização: **{total}**")

                # Exportar como XLSX
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Higienizado")
                    writer.close()
                st.download_button("⬇️ Baixar arquivo higienizado (.xlsx)", data=output.getvalue(), file_name="mailing_higienizado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")

