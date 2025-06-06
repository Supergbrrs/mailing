import streamlit as st
import pandas as pd
import re

# Função para carregar arquivos
def carregar_arquivo(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=None)  # Lê sem cabeçalho para detectar problemas
            df = ajustar_colunas(df)  # Ajusta colunas automaticamente se necessário
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado! Envie um CSV ou XLSX.")
            return None
        return df
    return None

# Função para ajustar colunas quando os dados vêm agrupados em uma única coluna
def ajustar_colunas(df):
    if df.shape[1] == 1:  # Verifica se há apenas uma coluna
        df = df.iloc[:, 0].str.split(';', expand=True)  # Separa os valores usando ";"
        df.columns = df.iloc[0]  # Usa a primeira linha como nomes das colunas
        df = df.iloc[1:].reset_index(drop=True)  # Remove a linha usada como cabeçalho
    return df

# Função para carregar a blacklist
def carregar_blacklist():
    try:
        blacklist = pd.read_csv("blacklist.csv", header=None, names=['Numero'])
        blacklist['Numero'] = blacklist['Numero'].astype(str)  
        return blacklist
    except Exception as e:
        st.error(f"Erro ao carregar a blacklist: {e}")
        return None

# Função para validar números
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
        # Verifica e renomeia colunas duplicadas
        if df.columns.duplicated().any():
            # Renomeia colunas duplicadas adicionando sufixos
            new_cols = []
            seen = {}
            for col in df.columns:
                if col == '':
                    col = 'vazio'
                if col in seen:
                    seen[col] += 1
                    new_col = f"{col}_{seen[col]}"
                else:
                    seen[col] = 0
                    new_col = col
                new_cols.append(new_col)
            df.columns = new_cols
            st.warning("⚠️ Foram encontradas colunas duplicadas no arquivo e elas foram renomeadas automaticamente.")

        st.write("📜 **Visualização dos dados do mailing:**")
        st.dataframe(df.head())

        # Identifica colunas de telefone (tel1, tel2, ...) e destino (des1, des2, ...)
        colunas_telefone = [col for col in df.columns if col.startswith("tel")]
        colunas_destino = [col for col in df.columns if col.startswith("des")]
        
        if not colunas_telefone and not colunas_destino:
            st.error("⚠️ Nenhuma coluna de telefone ou destino encontrada! Verifique o arquivo.")
        else:
            st.success(f"📌 Colunas identificadas: Telefones → {colunas_telefone}, Destinos → {colunas_destino}")
            
            # Carregando blacklist automaticamente
            blacklist = carregar_blacklist()
            if blacklist is not None:
                blacklist_set = set(blacklist["Numero"].values)  # Busca rápida

                for coluna in colunas_telefone + colunas_destino:
                    df[coluna] = df[coluna].astype(str)  # Converte para string
                    df[coluna] = df[coluna].apply(lambda x: "" if x in blacklist_set else x)
            
            # Contagem números válidos e inválidos (sem criar colunas status)
            total_validos = 0
            total_invalidos = 0
            for coluna in colunas_telefone + colunas_destino:
                valid_flags = df[coluna].apply(lambda x: validar_numero(x) == "Válido")
                total_validos += valid_flags.sum()
                total_invalidos += (~valid_flags).sum()

            st.write("📊 **Resumo Estatístico:**")
            st.write(f"✅ Números válidos após higienização: **{total_validos}**")
            st.write(f"❌ Números inválidos após higienização: **{total_invalidos}**")

            st.write("📜 **Visualização final do arquivo:**")
            st.dataframe(df)

            # Gerar arquivo Excel para download
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='mailing_higienizado')
                writer.save()
            buffer.seek(0)

            st.download_button(
                label="💾 Baixar mailing higienizado (XLSX)",
                data=buffer,
                file_name="mailing_higienizado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
