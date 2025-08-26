# Auditor PIS/COFINS - Lucro Presumido

Este é um aplicativo em Streamlit que analisa arquivos XML de Nota Fiscal Eletrônica (modelo 55), verifica os códigos CST de PIS e COFINS e os compara com uma tabela de referência, identificando inconsistências fiscais conforme o regime de Lucro Presumido.

## ⚙️ Requisitos

- Python 3.8+
- Pacotes: `streamlit`, `pandas`, `openpyxl`

## 📦 Instalação

```bash
pip install -r requirements.txt
```

## 🚀 Execução

```bash
streamlit run auditor_pis_cofins_app.py
```

## 📁 Funcionalidades

- Upload da tabela de referência em Excel.
- Upload múltiplo de arquivos XML.
- Leitura por item da NF-e.
- Validação de CFOP x CST conforme tabela.
- Relatório em Excel com divergências detectadas.

## 🌐 Publicação (opcional)

Você pode publicar este app gratuitamente no [Streamlit Cloud](https://streamlit.io/cloud).

1. Suba os arquivos `auditor_pis_cofins_app.py`, `requirements.txt` e `README.md` em um repositório GitHub.
2. Vá até Streamlit Cloud, conecte seu GitHub e publique o app.

---

Para dúvidas e suporte, entre em contato com seu desenvolvedor ou equipe de TI contábil.
