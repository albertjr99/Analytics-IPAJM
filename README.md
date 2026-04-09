# IPAJM Analytics Institucional

Sistema moderno e inovador de analytics para o Instituto de Previdência dos Servidores do Estado do Espírito Santo (IPAJM), desenvolvido em Python e otimizado para Dash/Plotly.

## 🚀 Funcionalidades

- **ETL Automatizado**: Processamento, limpeza e padronização de dados de Servidores Ativos, Inativos e Pensionistas.
- **Dashboards Interativos**: Visualização de KPIs, distribuições demográficas e financeiras.
- **Análises Avançadas**: Insights sobre pirâmide etária, remuneração média por cargo/órgão e evolução de contribuições.
- **Interface Moderna**: Design inspirado no padrão institucional, focado em UX e tomada de decisão.

## 🛠️ Tecnologias

- **Linguagem**: Python 3.11+
- **Processamento de Dados**: Pandas, PyArrow (formato Parquet para performance)
- **Visualização**: Dash, Plotly, Dash Bootstrap Components
- **Servidor Web**: Gunicorn (pronto para PythonAnywhere)

## 📁 Estrutura do Projeto

```text
/
├── app.py              # Aplicação principal (Dash)
├── etl_process.py      # Script de processamento de dados
├── analysis.py         # Geração de insights e estatísticas
├── data_processed.parquet # Dados unificados e otimizados
├── assets/             # Estilos CSS e imagens
│   └── custom.css      # Identidade visual personalizada
└── requirements.txt    # Dependências do projeto
```

## 💻 Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/albertjr99/Analytics_Gabriel.git
   cd Analytics_Gabriel
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o ETL (opcional, se os dados mudarem):
   ```bash
   python etl_process.py
   ```

4. Inicie o dashboard:
   ```bash
   python app.py
   ```
   Acesse em `http://localhost:8050`

## ☁️ Deploy no PythonAnywhere

Este projeto foi estruturado para funcionar perfeitamente no PythonAnywhere:

1. No painel do PythonAnywhere, vá em **Web** -> **Add a new web app**.
2. Escolha **Flask** (o Dash é baseado em Flask).
3. Aponte para o arquivo `app.py`.
4. No arquivo de configuração WSGI do PythonAnywhere, configure o objeto `application`:
   ```python
   from app import app
   application = app.server
   ```
5. Instale as dependências no terminal do PythonAnywhere:
   ```bash
   pip install dash dash-bootstrap-components pandas pyarrow openpyxl
   ```

## 📊 Insights Gerados

O sistema destaca automaticamente:
- **Pirâmide Etária**: Concentração de servidores por faixas.
- **Impacto Financeiro**: Médias salariais e totais de contribuição por categoria.
- **Top Cargos**: Identificação dos cargos com maior representatividade e remuneração.
- **Distribuição Geográfica**: Análise por UF e Órgãos do Estado.

---
Desenvolvido para o **IPAJM** - *Inovação e Transparência na Previdência.*
