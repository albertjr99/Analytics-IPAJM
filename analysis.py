import pandas as pd
import numpy as np
import os

def generate_insights():
    base_path = "/home/ubuntu/Analytics_Gabriel"
    df = pd.read_parquet(os.path.join(base_path, 'data_processed.parquet'))
    
    insights = {}
    
    # 1. Estatísticas por Categoria
    insights['por_categoria'] = df.groupby('CATEGORIA').agg({
        'IDADE': ['mean', 'median'],
        'VL_REMUNERACAO': ['mean', 'median', 'std', 'sum'],
        'ID_SERVIDOR_MATRICULA': 'count'
    }).round(2).to_dict()
    
    # 2. Top 10 Cargos (por remuneração média)
    top_cargos = df.groupby('NO_CARGO')['VL_REMUNERACAO'].mean().sort_values(ascending=False).head(10)
    insights['top_cargos_salario'] = top_cargos.to_dict()
    
    # 3. Distribuição por Sexo
    insights['dist_sexo'] = df['SEXO_DESC'].value_counts().to_dict()
    
    # 4. Outliers de Remuneração (Percentil 99)
    p99 = df['VL_REMUNERACAO'].quantile(0.99)
    outliers = df[df['VL_REMUNERACAO'] > p99].shape[0]
    insights['outliers_remuneracao'] = {'limite_p99': p99, 'contagem': outliers}
    
    # 5. Evolução por Órgão
    top_orgaos = df['NO_ORGAO'].value_counts().head(10).index
    insights['top_orgaos_contagem'] = df['NO_ORGAO'].value_counts().head(10).to_dict()
    
    # 6. Distribuição por UF (SG_UF)
    insights['dist_uf'] = df['SG_UF'].value_counts().to_dict()

    # Salvar insights em JSON para o dashboard ler rapidamente
    import json
    # Converter chaves para string para garantir serialização JSON
    def convert_keys(obj):
        if isinstance(obj, dict):
            return {str(k): convert_keys(v) for k, v in obj.items()}
        return obj

    with open(os.path.join(base_path, 'insights.json'), 'w') as f:
        json.dump(convert_keys(insights), f, indent=4)
    
    print("Análises e insights gerados com sucesso.")

if __name__ == "__main__":
    generate_insights()
