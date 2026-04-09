import pandas as pd
import numpy as np
import os

def load_and_preprocess(file_path, category):
    print(f"Processando {file_path}...")
    df = pd.read_excel(file_path)
    df['CATEGORIA'] = category
    
    # Padronização básica de nomes de colunas (remover espaços e colocar em maiúsculas)
    df.columns = [c.strip().upper() for c in df.columns]
    
    return df

def run_etl():
    base_path = "/home/ubuntu/Analytics_Gabriel"
    
    # Arquivos
    files = {
        'ATIVOS': os.path.join(base_path, 'SERVIDORES ATIVOS.xlsx'),
        'INATIVOS': os.path.join(base_path, 'SERVIDORES INATIVOS.xlsx'),
        'PENSIONISTAS': os.path.join(base_path, 'SERVIDORES PENSIONISTAS.xlsx')
    }
    
    dfs = []
    for cat, path in files.items():
        if os.path.exists(path):
            dfs.append(load_and_preprocess(path, cat))
    
    # Concatenar mantendo todas as colunas comuns
    full_df = pd.concat(dfs, axis=0, ignore_index=True)
    
    # --- Limpeza e Padronização ---
    
    # 1. Datas
    date_cols = [c for c in full_df.columns if c.startswith('DT_')]
    for col in date_cols:
        full_df[col] = pd.to_datetime(full_df[col], errors='coerce')
    
    # 2. Idade (baseada na data de nascimento)
    current_year = 2026 # Conforme contexto do sistema
    full_df['IDADE'] = current_year - full_df['DT_NASC_SERVIDOR'].dt.year
    
    # 3. Faixa Etária
    bins = [0, 18, 25, 35, 45, 55, 65, 75, 120]
    labels = ['<18', '18-25', '26-35', '36-45', '46-55', '56-65', '66-75', '>75']
    full_df['FAIXA_ETARIA'] = pd.cut(full_df['IDADE'], bins=bins, labels=labels).astype(str)
    
    # 4. Sexo
    full_df['SEXO_DESC'] = full_df['CO_SEXO_SERVIDOR'].map({1: 'Masculino', 2: 'Feminino'}).fillna('Não Informado')
    
    # 5. Tempo de Serviço (Anos)
    if 'DT_ING_SERV_PUB' in full_df.columns:
        full_df['TEMPO_SERVICO_ANOS'] = (pd.to_datetime('2026-04-09') - full_df['DT_ING_SERV_PUB']).dt.days / 365.25
    
    # 6. Limpeza de valores monetários (garantir float)
    money_cols = ['VL_REMUNERACAO', 'VL_BASE_CALCULO', 'VL_CONTRIBUICAO']
    for col in money_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce').fillna(0)
            
    # --- Correção Final para Parquet ---
    # Converter todas as colunas que ainda são do tipo 'object' para string
    # Isso resolve problemas com tipos mistos que o PyArrow não gosta
    for col in full_df.columns:
        if full_df[col].dtype == 'object':
            full_df[col] = full_df[col].astype(str)

    # Salvar dados processados para uso no dashboard
    output_path = os.path.join(base_path, 'data_processed.parquet')
    full_df.to_parquet(output_path, index=False)
    print(f"ETL concluído. Dados salvos em {output_path}")
    
    # Gerar um resumo estatístico básico
    summary = {
        'total_servidores': len(full_df),
        'por_categoria': full_df['CATEGORIA'].value_counts().to_dict(),
        'media_salarial': full_df['VL_REMUNERACAO'].mean(),
        'media_idade': full_df['IDADE'].mean()
    }
    print("Resumo:", summary)

if __name__ == "__main__":
    run_etl()
