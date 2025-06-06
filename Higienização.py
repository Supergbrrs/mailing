import streamlit as st
import pandas as pd
import re

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

# Função para ajustar colunas quando os dados vêm agrupados em uma única coluna
def ajustar_colunas(df):
    if df.shape[1] == 1:
        df = df.iloc[:, 0].str.split(';', expand=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
    return df

# Função para renomear colunas duplicadas e retornar quais foram alteradas
def renomear_colunas_duplicadas(df):
    cols = pd.Series(df.columns)
    renomeadas = {}
    for dup in cols[cols.duplicated()].unique():
        dup_indices = cols[cols == dup].index.tolist()
        for i, idx in enumerate(dup_indices[1:], start=1):
            novo_nome = f"{cols[idx]}_{i}"
            renomeadas[cols[idx]] = renomeadas.get(cols[idx], []) + [novo_nome]
            cols[idx] = novo_nome
    df.columns = cols
    return df, renomeadas

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
        df, renomeadas = renomear_colunas_duplicadas(df)
        
        if renomeadas:
            mensagens = []
            for original, novos in renomeadas.items():
                mensagens.append(f"Coluna '{original}' renomeada para: {', '.join(novos)}")
            st.warning("Colunas duplicadas foram renomeadas para evitar erros:\n\n" + "\n".join(mensagens))
        
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
                for coluna in colunas_telefone + colunas_destino:
                    df[coluna] = df[coluna].astype(str)  # Converte para string
                    df[coluna] = df[coluna].apply(lambda x: "" if x in blacklist["Numero"].values else x)  # Remove números da blacklist
                    
                    # Aplicando validação
                    # Se não quiser criar colunas Status, pode comentar a linha abaixo
                    # df[f"Status_{coluna}"] = df[coluna].apply(validar_numero)
            
            # Exibir estatísticas
            total_validos = sum(
                len(df[df[coluna].apply(validar_numero) == "Válido"])
                for coluna in colunas_telefone + colunas_destino
            )
            total_invalidos = sum(
                len(df[df[coluna].apply(validar_numero) == "Inválido"])
                for coluna in colunas_telefone + colunas_destino
            )

            st.write("📊 **Resumo Estatístico:**")
            st.write(f"✅ Números válidos após higienização: **{total_validos}**")
            st.write(f"❌ Números inválidos após higienização: **{total_invalidos}**")

            st.write("📜 **Visualização final do arquivo:**")
            st.dataframe(df)

            # Download do arquivo em XLSX
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

