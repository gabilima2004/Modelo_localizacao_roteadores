"""
extracao.py — Extração de dados do QuestDB

============================================================
ETAPA 2 DO PROJETO: COLETA DE DADOS
============================================================

Este arquivo é responsável por:
  1. Conectar ao QuestDB
  2. Extrair a tabela `routers` (pequena, ~5000 linhas) de uma vez
  3. Extrair a tabela `device_metrics` (enorme, ~864M linhas) por dia
  4. Salvar tudo em arquivos locais (CSV ou Parquet)

ESTRATÉGIA DE AMOSTRAGEM:
  - routers: tabela estática, poucas linhas → extrai tudo
  - device_metrics: ~7,2M linhas por dia → extrai dia a dia, salva
    cada dia em um arquivo separado na pasta data/

COMO USAR:
  python extracao.py

  O script vai:
  1. Extrair routers e salvar em data/routers.csv
  2. Para cada dia no período definido, extrair device_metrics
     e salvar em data/metrics_YYYY-MM-DD.csv
  3. Pular dias que já foram extraídos (para retomar interrupções)
============================================================
"""

import os
import pandas as pd
import psycopg2  # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore

# ============================================================
# CONFIGURAÇÕES — ajuste estes valores conforme seu ambiente
# ============================================================

# Dados de conexão com o QuestDB
# QuestDB aceita conexões PostgreSQL na porta 8812 por padrão
QUESTDB_HOST = "localhost"
QUESTDB_PORT = 8812
QUESTDB_USER = "admin"
QUESTDB_PASSWORD = "quest"
QUESTDB_DATABASE = "qdb"

# Período de dados a extrair (formato: YYYY-MM-DD)
DATA_INICIO = "2025-04-01"
DATA_FIM = "2025-07-24"

# Pasta onde salvar os arquivos extraídos
PASTA_DADOS = "data"

# Formato de saída: "csv" ou "parquet"
# Dica: comece com "csv" para entender o formato, depois mude para "parquet"
FORMATO_SAIDA = "csv"


# ============================================================
# FUNÇÃO 1: Conectar ao QuestDB
# ============================================================
def conectar():
    """Abre e retorna uma conexão com o QuestDB.

    O QuestDB implementa o protocolo PostgreSQL wire, então usamos
    psycopg2 (o driver PostgreSQL padrão do Python) para conectar.

    RealDictCursor faz com que cada linha venha como um dicionário
    {nome_coluna: valor}, o que facilita converter para DataFrame.

    Retorna:
        Um objeto de conexão psycopg2.

    Levanta:
        psycopg2.OperationalError se não conseguir conectar.
    """
    conn = psycopg2.connect(
        host=QUESTDB_HOST,
        port=QUESTDB_PORT,
        user=QUESTDB_USER,
        password=QUESTDB_PASSWORD,
        database=QUESTDB_DATABASE,
        cursor_factory=RealDictCursor,
    )
    print(f"[conectar] Conectado ao QuestDB em {QUESTDB_HOST}:{QUESTDB_PORT}")
    return conn


# ============================================================
# FUNÇÃO 2: Extrair a tabela routers
# ============================================================
def extrair_routers(conn):
    """Extrai a tabela `routers` (dados de localização dos roteadores).

    Esta tabela é estática e pequena (~5000 linhas), então podemos
    trazer tudo de uma vez sem problema de memória.

    Retorna:
        DataFrame do pandas com os dados da tabela.
    """
    query = "SELECT * FROM routers"

    print("[extrair_routers] Executando query...")
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    df = pd.DataFrame(rows)
    print(f"[extrair_routers] {len(df)} roteadores extraídos")
    return df


# ============================================================
# FUNÇÃO 3: Extrair device_metrics de um dia específico
# ============================================================
def extrair_metrics_dia(conn, data):
    """Extrai device_metrics de um único dia.

    Por que por dia? Porque a tabela inteira tem ~864 milhões de linhas
    (5000 roteadores × 1440 minutos/dia × 120 dias). Carregar tudo de
    uma vez esgotaria a memória. Um dia tem ~7,2 milhões de linhas,
    que é gerenciável.

    Parâmetros:
        conn: conexão com QuestDB
        data: string "YYYY-MM-DD" ou objeto datetime

    Retorna:
        DataFrame com as métricas daquele dia.
    """
    # Converte para string no formato correto, caso venha como datetime
    data_str = pd.Timestamp(data).strftime("%Y-%m-%d")
    dia_seguinte = (pd.Timestamp(data) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    # A query filtra por um intervalo de 24 horas:
    # timestamp >= '2025-04-01' AND timestamp < '2025-04-02'
    # Usamos < (menor que) e não <= para não pegar o dia seguinte
    query = f"""
        SELECT * FROM device_metrics
        WHERE timestamp >= '{data_str}'
          AND timestamp < '{dia_seguinte}'
    """

    print(f"[extrair_metrics_dia] Extraindo dia {data_str}...")
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    df = pd.DataFrame(rows)
    print(f"[extrair_metrics_dia] {len(df)} linhas para {data_str}")
    return df


# ============================================================
# FUNÇÃO 4: Salvar DataFrame em arquivo
# ============================================================
def salvar(df, nome_arquivo):
    """Salva um DataFrame em arquivo (CSV ou Parquet).

    A extensão do arquivo é adicionada automaticamente conforme
    o FORMATO_SAIDA configurado no topo do arquivo.

    Parâmetros:
        df: DataFrame a salvar
        nome_arquivo: nome base (sem extensão), ex: "routers" ou "metrics_2025-04-01"
    """
    # Garante que a pasta existe
    os.makedirs(PASTA_DADOS, exist_ok=True)

    if FORMATO_SAIDA == "csv":
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.csv")
        df.to_csv(caminho, index=False)
    elif FORMATO_SAIDA == "parquet":
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.parquet")
        df.to_parquet(caminho, index=False)
    else:
        raise ValueError(f"Formato desconhecido: {FORMATO_SAIDA}")

    print(f"[salvar] {len(df)} linhas salvas em {caminho}")


# ============================================================
# FUNÇÃO 5: Verificar se arquivo já existe (para não re-extrair)
# ============================================================
def ja_existe(nome_arquivo):
    """Verifica se um arquivo de dados já existe na pasta.

    Isso permite retomar a extração se ela for interrompida —
    dias já baixados são pulados automaticamente.
    """
    if FORMATO_SAIDA == "csv":
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.csv")
    else:
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.parquet")
    return os.path.exists(caminho)


# ============================================================
# FUNÇÃO PRINCIPAL: Orquestra toda a extração
# ============================================================
def main():
    """Função principal que coordena toda a extração.

    Passos:
    1. Conecta ao QuestDB
    2. Extrai e salva a tabela routers (se ainda não existir)
    3. Para cada dia no período, extrai e salva device_metrics
       (pulando dias já extraídos)
    4. Fecha a conexão
    """
    print("=" * 60)
    print("  EXTRAÇÃO DE DADOS — MODELO RESIDENCIAL COMERCIAL")
    print("=" * 60)

    # 1. Conecta
    conn = conectar()

    try:
        # 2. Extrai routers (se ainda não foi extraído)
        if not ja_existe("routers"):
            df_routers = extrair_routers(conn)
            salvar(df_routers, "routers")
        else:
            print("[main] routers já extraído, pulando...")

        # 3. Extrai device_metrics dia a dia
        dias = pd.date_range(start=DATA_INICIO, end=DATA_FIM, freq="D")
        print(f"[main] {len(dias)} dias a processar ({DATA_INICIO} a {DATA_FIM})")

        for i, dia in enumerate(dias):
            nome_dia = dia.strftime("%Y-%m-%d")
            nome_arquivo = f"metrics_{nome_dia}"

            if ja_existe(nome_arquivo):
                print(f"[main] ({i+1}/{len(dias)}) {nome_dia} já existe, pulando...")
                continue

            df_dia = extrair_metrics_dia(conn, dia)

            # Se o dia não tem dados (ex: futuro), pula
            if len(df_dia) == 0:
                print(f"[main] ({i+1}/{len(dias)}) {nome_dia} sem dados, pulando...")
                continue

            salvar(df_dia, nome_arquivo)

    finally:
        # 4. Fecha a conexão (sempre, mesmo se houver erro)
        conn.close()
        print("[main] Conexão fechada.")

    print("=" * 60)
    print("  EXTRAÇÃO CONCLUÍDA!")
    print("=" * 60)


# ============================================================
# Executa se o arquivo for chamado diretamente
# python extracao.py
# ============================================================
if __name__ == "__main__":
    main()