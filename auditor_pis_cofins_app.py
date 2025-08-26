# v2: Auditor PIS/COFINS com validação CFOP x CST (ICMS + PIS/COFINS)
import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import re
from io import BytesIO

st.set_page_config(page_title="Auditor PIS/COFINS", layout="wide")
st.title("🔍 Auditor PIS/COFINS - Lucro Presumido")

# ----------------------
# Helpers
# ----------------------

def detect_ns(root):
    """Detecta o namespace do XML da NF-e dinamicamente."""
    m = re.match(r"\{(.*)\}", root.tag)
    uri = m.group(1) if m else "http://www.portalfiscal.inf.br/nfe"
    return {"nfe": uri}


def norm_cfop(cfop_str: str) -> str:
    if cfop_str is None:
        return ""
    s = re.sub(r"[^0-9]", "", str(cfop_str))  # remove ponto, etc.
    return s[-4:].zfill(4)


def pad2(s):
    if s is None or s == "":
        return None
    try:
        s = str(int(float(str(s).strip())))  # lida com 1.0 etc.
    except Exception:
        s = str(s).strip()
    if s.isdigit() and len(s) == 1:
        return f"0{s}"
    return s


def icms_expected_str(v):
    """Converte exemplos da planilha para CST ICMS esperado ('00','41','60').
    Se vier 100 ou vazio, retorna None (sem regra)."""
    if pd.isna(v):
        return None
    try:
        n = int(float(v))
        if n == 0:
            return "00"
        if n == 100:
            return None
        return str(n)
    except Exception:
        s = str(v).strip()
        return s or None


def extract_pis_cst(det, ns):
    for node in ["PISAliq", "PISQtde", "PISNT", "PISOutr"]:
        n = det.find(f".//nfe:PIS/nfe:{node}/nfe:CST", ns)
        if n is not None and n.text:
            return n.text.strip()
    n = det.find(f".//nfe:PIS//nfe:CST", ns)
    return n.text.strip() if n is not None and n.text else None


def extract_cofins_cst(det, ns):
    for node in ["COFINSAliq", "COFINSQtde", "COFINSNT", "COFINSOutr"]:
        n = det.find(f".//nfe:COFINS/nfe:{node}/nfe:CST", ns)
        if n is not None and n.text:
            return n.text.strip()
    n = det.find(f".//nfe:COFINS//nfe:CST", ns)
    return n.text.strip() if n is not None and n.text else None


def extract_icms_cst(det, ns):
    """Retorna (grupo_icms, codigo, tipo) onde tipo in {"CST","CSOSN"}."""
    icms = det.find(".//nfe:ICMS", ns)
    if icms is None:
        return (None, None, None)
    children = list(icms)
    if not children:
        return (None, None, None)
    grp = children[0]
    grp_name = re.sub(r"^\{.*\}", "", grp.tag)
    cst = grp.find(".//nfe:CST", ns)
    if cst is not None and cst.text:
        return (grp_name, cst.text.strip(), "CST")
    csosn = grp.find(".//nfe:CSOSN", ns)
    if csosn is not None and csosn.text:
        return (grp_name, csosn.text.strip(), "CSOSN")
    return (grp_name, None, None)

# ----------------------
# UI - Uploads
# ----------------------

st.sidebar.header("1. Planilha de Regras (CFOP x CST)")
regras_file = st.sidebar.file_uploader("Envie o Excel com as regras (CFOP, CST ICMS, CST PIS/COFINS)", type=["xlsx"])

st.sidebar.header("2. Arquivos XML de NF-e")
xml_files = st.sidebar.file_uploader("Envie os XMLs de NF-e (modelo 55)", type=["xml"], accept_multiple_files=True)

if regras_file and xml_files:
    try:
        df_rules = pd.read_excel(regras_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Erro ao ler a planilha de regras: {e}")
        st.stop()

    cols = {c.lower(): c for c in df_rules.columns}
    col_cfop = cols.get("cfop") or "CFOP"
    col_icms = cols.get("cst icms (exemplo)") or cols.get("cst icms") or "CST ICMS (Exemplo)"
    col_piscof = cols.get("cst pis/cofins") or cols.get("cst pis_cofins") or "CST PIS/COFINS"

    df_rules["CFOP_norm"] = df_rules[col_cfop].astype(str).str.replace(".", "", regex=False).str.extract(r"(\d+)").fillna("")
    df_rules["CFOP_norm"] = df_rules["CFOP_norm"].apply(lambda x: x[-4:].zfill(4))

    df_rules["ICMS_esp"] = df_rules[col_icms].apply(icms_expected_str)
    df_rules["PISCOF_esp"] = df_rules[col_piscof].apply(pad2)

    rule_map = df_rules.set_index("CFOP_norm")[ ["ICMS_esp","PISCOF_esp", col_cfop] ]

    resultados = []

    for file in xml_files:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            ns = detect_ns(root)

            nNF_node = root.find(".//nfe:ide/nfe:nNF", ns)
            nNF = nNF_node.text.strip() if nNF_node is not None and nNF_node.text else "?"

            for det in root.findall(".//nfe:det", ns):
                nItem = det.attrib.get("nItem")
                cfop_node = det.find(".//nfe:CFOP", ns)
                cfop_xml = cfop_node.text.strip() if cfop_node is not None and cfop_node.text else ""
                cfop_norm = norm_cfop(cfop_xml)

                pis_cst = extract_pis_cst(det, ns)
                cof_cst = extract_cofins_cst(det, ns)
                icms_grp, icms_cst, icms_tipo = extract_icms_cst(det, ns)

                esp_icms = esp_piscof = None
                regra_cfop_fmt = None
                if cfop_norm in rule_map.index:
                    esp_icms = rule_map.loc[cfop_norm, "ICMS_esp"]
                    esp_piscof = rule_map.loc[cfop_norm, "PISCOF_esp"]
                    regra_cfop_fmt = str(rule_map.loc[cfop_norm, col_cfop])

                divergencias = []
                if icms_tipo == "CSOSN":
                    divergencias.append("ICMS com CSOSN (Simples Nacional) em contribuinte Lucro Presumido")
                if esp_icms is not None and icms_cst is not None and icms_cst != esp_icms:
                    divergencias.append(f"ICMS CST {icms_cst} difere do esperado {esp_icms} para CFOP {regra_cfop_fmt or cfop_xml}")
                if esp_piscof is not None:
                    if pis_cst and pis_cst != esp_piscof:
                        divergencias.append(f"PIS CST {pis_cst} difere do esperado {esp_piscof}")
                    if cof_cst and cof_cst != esp_piscof:
                        divergencias.append(f"COFINS CST {cof_cst} difere do esperado {esp_piscof}")

                if divergencias:
                    resultados.append({
                        "Nota Fiscal": nNF,
                        "Item": nItem,
                        "CFOP(XML)": cfop_xml,
                        "CFOP(Regra)": regra_cfop_fmt or "-",
                        "ICMS CST (XML)": icms_cst or "-",
                        "PIS CST (XML)": pis_cst or "-",
                        "COFINS CST (XML)": cof_cst or "-",
                        "ICMS CST Esperado": esp_icms or "-",
                        "PIS/COFINS CST Esperado": esp_piscof or "-",
                        "Justificativa": "; ".join(divergencias)
                    })
        except Exception as e:
            st.error(f"Erro ao processar {getattr(file,'name', 'XML')}: {e}")

    if resultados:
        df_result = pd.DataFrame(resultados)
        st.success(f"Análise concluída! Foram encontradas {len(df_result)} divergências.")
        st.dataframe(df_result, use_container_width=True)

        towrite = BytesIO()
        df_result.to_excel(towrite, index=False, sheet_name='Divergências')
        towrite.seek(0)
        st.download_button(
            "📥 Baixar Relatório Excel",
            data=towrite,
            file_name="divergencias_cst_cfop_icms_piscofins.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Nenhuma divergência encontrada conforme a planilha de regras enviada.")
else:
    st.info("Envie a planilha de regras (Excel) e os XMLs para iniciar a análise.")
