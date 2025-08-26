import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import os
from io import BytesIO

st.set_page_config(page_title="Auditor PIS/COFINS", layout="wide")
st.title("🔍 Auditor PIS/COFINS - Lucro Presumido")

# Upload da tabela de referência
st.sidebar.header("1. Tabela de Referência CST")
tabela_file = st.sidebar.file_uploader("Envie o arquivo Excel com os CSTs válidos", type=["xlsx"])

# Upload dos arquivos XML
st.sidebar.header("2. Arquivos XML de NF-e")
xml_files = st.sidebar.file_uploader("Envie os arquivos XML de NF-e (modelo 55)", type=["xml"], accept_multiple_files=True)

if tabela_file and xml_files:
    # Leitura da tabela de referência
    df_ref = pd.read_excel(tabela_file)

    resultados = []

    for file in xml_files:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

            nNF = root.find(".//nfe:ide/nfe:nNF", ns).text

            for det in root.findall(".//nfe:det", ns):
                nItem = det.attrib.get("nItem")
                cfop = det.find(".//nfe:CFOP", ns).text
                cst_pis = det.find(".//nfe:PIS//nfe:CST", ns)
                cst_cofins = det.find(".//nfe:COFINS//nfe:CST", ns)

                cst_pis = cst_pis.text if cst_pis is not None else "N/A"
                cst_cofins = cst_cofins.text if cst_cofins is not None else "N/A"

                # Validação simples com base na tabela
                esperado = df_ref[df_ref['CST'] == int(cst_pis)] if cst_pis.isdigit() else pd.DataFrame()

                if not esperado.empty:
                    just = esperado.iloc[0]['Quando Utilizar']
                else:
                    just = "CST PIS não esperado para CFOP informado no Lucro Presumido"

                if esperado.empty or (cfop.startswith("5") and int(cst_pis) in [4, 6, 7, 8, 9]):
                    resultados.append({
                        "Nota Fiscal": nNF,
                        "Item": nItem,
                        "CFOP": cfop,
                        "CST PIS": cst_pis,
                        "CST COFINS": cst_cofins,
                        "CST Esperado": esperado.iloc[0]['CST'] if not esperado.empty else "-",
                        "Justificativa": just
                    })

        except Exception as e:
            st.error(f"Erro ao processar {file.name}: {e}")

    if resultados:
        df_result = pd.DataFrame(resultados)
        st.success("Análise concluída com divergências identificadas!")
        st.dataframe(df_result)

        towrite = BytesIO()
        df_result.to_excel(towrite, index=False, sheet_name='Divergências')
        towrite.seek(0)

        st.download_button("📥 Baixar Relatório Excel", data=towrite, file_name="divergencias_cst.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Nenhuma divergência encontrada nos arquivos XML enviados.")
