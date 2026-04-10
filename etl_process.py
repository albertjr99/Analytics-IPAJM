import pandas as pd
import numpy as np
import os

def load_and_preprocess(file_path, category):
    print(f"Processando {file_path}...")
    df = pd.read_excel(file_path)
    df['CATEGORIA'] = category
    df.columns = [c.strip().upper() for c in df.columns]
    return df

def process_recadastramento(base_path):
    """Processa as planilhas de recadastramento (prova de vida)."""
    rec_file = os.path.join(base_path, 'RCADASTRAMENTO 2025 - RECADASTRADOS.xlsx')
    nao_file = os.path.join(base_path, 'RELATORIO RECADASTRAMENTO 2025 - NÃO RECADASTRADOS.xlsx')

    frames = []
    for path, status in [(rec_file, 'RECADASTRADO'), (nao_file, 'NÃO RECADASTRADO')]:
        if os.path.exists(path):
            print(f"Processando recadastramento: {path}...")
            df = pd.read_excel(path)
            df.columns = [c.strip().upper() for c in df.columns]
            df['STATUS_RECAD'] = status
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    rdf = pd.concat(frames, ignore_index=True)

    # Padronizar colunas
    rdf.rename(columns={
        'NOME_CATEGORIA': 'RECAD_CATEGORIA',
        'TIPORECAD': 'MODALIDADE_RECAD',
        'ORGAO': 'RECAD_ORGAO',
        'CARGO': 'RECAD_CARGO',
    }, inplace=True)

    # Sexo descritivo
    rdf['SEXO_DESC'] = rdf['SEXO'].map({'M': 'Masculino', 'F': 'Feminino'}).fillna('Não Informado')

    # Faixa etária
    rdf['IDADE'] = pd.to_numeric(rdf['IDADE'], errors='coerce')
    bins = [0, 50, 60, 70, 80, 200]
    labels = ['<50', '50-60', '61-70', '71-80', '80+']
    rdf['FAIXA_ETARIA_RECAD'] = pd.cut(rdf['IDADE'], bins=bins, labels=labels).astype(str)

    # Modalidade — preencher NaN como "Pendente" (não recadastrados)
    rdf['MODALIDADE_RECAD'] = rdf['MODALIDADE_RECAD'].fillna('Pendente')

    # Mês de aniversário descritivo
    meses = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',
             7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
    rdf['MES_ANIV_DESC'] = rdf['MES_ANIVERSARIO'].map(meses).fillna('N/I')

    # Classificar categoria simplificada
    cat_map = {
        'Inativos': 'Inativos',
        'Pensionistas': 'Pensionistas',
        'Ativo-AGP': 'Ativos',
        'Ativo-AFP': 'Ativos',
        'Ativo-ATIVO': 'Ativos',
        'Ativo-INATIVO': 'Ativos',
    }
    rdf['RECAD_CAT_SIMPLES'] = rdf['RECAD_CATEGORIA'].map(cat_map).fillna('Outros')

    # Converter object cols para string (parquet)
    for col in rdf.columns:
        if rdf[col].dtype == 'object':
            rdf[col] = rdf[col].astype(str)

    return rdf


def run_etl():
    base_path = os.path.dirname(os.path.abspath(__file__))

    # ── 1. Servidores (Ativos, Inativos, Pensionistas) ──
    files = {
        'ATIVOS': os.path.join(base_path, 'SERVIDORES ATIVOS.xlsx'),
        'INATIVOS': os.path.join(base_path, 'SERVIDORES INATIVOS.xlsx'),
        'PENSIONISTAS': os.path.join(base_path, 'SERVIDORES PENSIONISTAS.xlsx')
    }

    dfs = []
    for cat, path in files.items():
        if os.path.exists(path):
            dfs.append(load_and_preprocess(path, cat))

    full_df = pd.concat(dfs, axis=0, ignore_index=True)

    # Datas
    date_cols = [c for c in full_df.columns if c.startswith('DT_')]
    for col in date_cols:
        full_df[col] = pd.to_datetime(full_df[col], errors='coerce')

    # Idade
    current_year = 2026
    full_df['IDADE'] = current_year - full_df['DT_NASC_SERVIDOR'].dt.year

    # Faixa Etária
    bins = [0, 18, 25, 35, 45, 55, 65, 75, 120]
    labels = ['<18', '18-25', '26-35', '36-45', '46-55', '56-65', '66-75', '>75']
    full_df['FAIXA_ETARIA'] = pd.cut(full_df['IDADE'], bins=bins, labels=labels).astype(str)

    # Sexo
    full_df['SEXO_DESC'] = full_df['CO_SEXO_SERVIDOR'].map({1: 'Masculino', 2: 'Feminino'}).fillna('Não Informado')

    # Tempo de Serviço
    if 'DT_ING_SERV_PUB' in full_df.columns:
        full_df['TEMPO_SERVICO_ANOS'] = (pd.to_datetime('2026-04-09') - full_df['DT_ING_SERV_PUB']).dt.days / 365.25

    # Monetário
    money_cols = ['VL_REMUNERACAO', 'VL_BASE_CALCULO', 'VL_CONTRIBUICAO']
    for col in money_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce').fillna(0)

    # Object → str
    for col in full_df.columns:
        if full_df[col].dtype == 'object':
            full_df[col] = full_df[col].astype(str)

    full_df.to_parquet(os.path.join(base_path, 'data_processed.parquet'), index=False)
    print(f"Servidores: {len(full_df)} registros salvos")

    # ── 2. Recadastramento ──
    rdf = process_recadastramento(base_path)
    if not rdf.empty:
        rdf.to_parquet(os.path.join(base_path, 'data_recadastramento.parquet'), index=False)
        print(f"Recadastramento: {len(rdf)} registros salvos")

        # Resumo
        total = len(rdf)
        recad = len(rdf[rdf['STATUS_RECAD'] == 'RECADASTRADO'])
        pct = recad / total * 100 if total else 0
        print(f"  Recadastrados: {recad} ({pct:.1f}%)")
        print(f"  Não Recadastrados: {total - recad} ({100-pct:.1f}%)")
    else:
        print("Nenhum arquivo de recadastramento encontrado.")

    summary = {
        'total_servidores': len(full_df),
        'por_categoria': full_df['CATEGORIA'].value_counts().to_dict(),
        'media_salarial': full_df['VL_REMUNERACAO'].mean(),
        'media_idade': full_df['IDADE'].mean()
    }
    print("Resumo:", summary)

if __name__ == "__main__":
    run_etl()
