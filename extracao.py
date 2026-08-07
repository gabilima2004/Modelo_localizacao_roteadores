"""
extracao.py — Extração de dados do QuestDB

============================================================
ETAPA 2 DO PROJETO: COLETA DE DADOS
============================================================

Este arquivo é responsável por:
  1. Conectar ao QuestDB
  2. Extrair a tabela `routers` (~6000 roteadores únicos, série temporal) de uma vez
     e deduplicar pegando a versão mais recente de cada roteador
  3. Extrair a tabela `device_metrics` (enorme, ~15,8M linhas/dia) por dia
  4. Salvar tudo em arquivos locais (CSV ou Parquet) na pasta data/raw/

ESTRATÉGIA DE AMOSTRAGEM:
  - routers: série temporal com ~12.000 linhas → deduplica e salva ~6.000 únicos
  - device_metrics: ~15,8M linhas por dia → extrai dia a dia, salva
    cada dia em um arquivo separado na pasta data/raw/

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
import time
import pandas as pd
import psycopg2  # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore

# ============================================================
# CONFIGURAÇÕES — ajuste estes valores conforme seu ambiente
# ============================================================

# Dados de conexão com o QuestDB
# QuestDB aceita conexões PostgreSQL na porta 8812 por padrão
QUESTDB_HOST = "10.246.47.168"
QUESTDB_PORT = 8812
QUESTDB_USER = "admin"
QUESTDB_PASSWORD = "quest"
QUESTDB_DATABASE = "qdb"

# Período de dados a extrair (formato: YYYY-MM-DD)
#DATA_INICIO = "2025-04-01"
#DATA_FIM = "2025-07-28"
DATA_INICIO = "2026-04-01"
DATA_FIM = "2026-07-20"

# Pasta onde salvar os arquivos extraídos (dados brutos)
PASTA_DADOS = "data/raw"

# Formato de saída: "csv" ou "parquet"
# Dica: comece com "csv" para entender o formato, depois mude para "parquet"
FORMATO_SAIDA = "csv"

# Se True, deleta o CSV de métricas após processar as features
# (Opção B: extrair, processar features, deletar dado bruto)
# Isso economiza disco — 4 meses de CSV seriam ~180GB!
DELETAR_APOS_PROCESSAR = True


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

    Esta tabela é uma série temporal — cada atualização de cadastro cria
    uma nova linha. Alguns roteadores têm dezenas de linhas (bug de coleta
    que recria o registro com location=null).

    Estratégia de deduplicação:
    1. Ordenar por timestamp (mais recente primeiro)
    2. Priorizar linhas que TÊM location (não null)
    3. Pegar a primeira linha de cada router_mac

    Assim, se a linha mais recente tem location=null (bug de coleta),
    mas uma linha anterior tem endereço, usamos a anterior.
    Isso recupera roteadores que estavam sem localização.
    """
    query = "SELECT router_mac, timestamp, manufacturer, model, user_ppp, location, city, state, latitude, longitude FROM routers"

    print("[extrair_routers] Executando query...")
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    df = pd.DataFrame(rows)
    print(f"[extrair_routers] {len(df)} linhas brutas")

    # Criar coluna auxiliar: True se location NÃO é null
    # Ordenar por essa coluna (True primeiro) e depois por timestamp (mais recente)
    df["tem_location"] = df["location"].notna()
    df = df.sort_values(by=["tem_location", "timestamp"], ascending=[False, False])

    # Pegar a primeira linha de cada router_mac (prioriza quem tem location)
    df_routers_unicos = df.drop_duplicates("router_mac", keep="first")

    # Remover coluna auxiliar
    df_routers_unicos = df_routers_unicos.drop(columns=["tem_location"])

    # Estatísticas
    com_loc = df_routers_unicos["location"].notna().sum()
    sem_loc = df_routers_unicos["location"].isna().sum()
    print(f"[extrair_routers] {len(df_routers_unicos)} roteadores únicos")
    print(f"[extrair_routers]   Com localização: {com_loc}")
    print(f"[extrair_routers]   Sem localização: {sem_loc} ({sem_loc/len(df_routers_unicos)*100:.1f}%)")

    return df_routers_unicos


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
        SELECT device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down FROM device_metrics
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
# FUNÇÃO 6: Deletar arquivo de dados brutos
# ============================================================
def deletar_arquivo(nome_arquivo):
    """Deleta um arquivo de dados brutos após processar as features.

    Isso economiza disco — os dados brutos (1,5GB/dia) não precisam
    ficar guardados depois que as features (1MB/dia) foram calculadas.
    """
    if FORMATO_SAIDA == "csv":
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.csv")
    else:
        caminho = os.path.join(PASTA_DADOS, f"{nome_arquivo}.parquet")

    if os.path.exists(caminho):
        os.remove(caminho)
        print(f"[deletar] {caminho} removido (liberou disco)")


# ============================================================
# FUNÇÃO 7: Verificar se as features de um dia já foram processadas
# ============================================================
def features_ja_processadas(nome_dia):
    """Verifica se as features de um dia já foram processadas.

    Com a Opção B (DELETAR_APOS_PROCESSAR=True), o CSV bruto é deletado
    após processar. Então não podemos verificar data/raw/ — precisamos
    verificar data/processed/features_YYYY-MM-DD.csv (o resultado).

    Parâmetros:
        nome_dia: string "YYYY-MM-DD"
    """
    caminho = os.path.join("data", "processed", f"features_{nome_dia}.csv")
    return os.path.exists(caminho)


# ============================================================
# FUNÇÃO PRINCIPAL: Orquestra toda a extração
# ============================================================
def main():
    """Função principal que coordena toda a extração.

    Passos:
    1. Conecta ao QuestDB
    2. Extrai e salva a tabela routers (se ainda não existir)
    3. Para cada dia no período:
       a. Extrai device_metrics e salva CSV
       b. Processa as features (chama features.py)
       c. Se DELETAR_APOS_PROCESSAR=True, deleta o CSV bruto
    4. Fecha a conexão

    Isso é a "Opção B": extrair, processar features, deletar dado bruto.
    Economiza disco — só ficam as features (pequenas), não os dados brutos.
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

            # Verificação depende do modo:
            # - Se DELETAR_APOS_PROCESSAR=True: verifica as features (data/processed/)
            #   (porque o CSV bruto foi deletado)
            # - Se DELETAR_APOS_PROCESSAR=False: verifica o CSV bruto (data/raw/)
            if DELETAR_APOS_PROCESSAR:
                if features_ja_processadas(nome_dia):
                    print(f"[main] ({i+1}/{len(dias)}) {nome_dia} já processado, pulando...")
                    continue
            else:
                if ja_existe(nome_arquivo):
                    print(f"[main] ({i+1}/{len(dias)}) {nome_dia} já existe, pulando...")
                    continue

            # Tenta extrair com reconexão automática (QuestDB cai às vezes)
            tentativas = 0
            max_tentativas = 3
            while tentativas < max_tentativas:
                try:
                    df_dia = extrair_metrics_dia(conn, dia)
                    break  # sucesso, sai do while
                except Exception as e:
                    tentativas += 1
                    print(f"[main] Erro ao extrair {nome_dia} (tentativa {tentativas}/{max_tentativas}): {e}")
                    if tentativas < max_tentativas:
                        print(f"[main] Reconectando ao QuestDB...")
                        try:
                            conn.close()
                        except:
                            pass
                        time.sleep(5)  # espera 5 segundos antes de reconectar
                        conn = conectar()
                    else:
                        print(f"[main] ❌ Falha após {max_tentativas} tentativas. Pulando {nome_dia}.")
                        df_dia = pd.DataFrame()  # vazio, vai pular

            # Se o dia não tem dados (ex: futuro), pula
            if len(df_dia) == 0:
                print(f"[main] ({i+1}/{len(dias)}) {nome_dia} sem dados, pulando...")
                continue

            salvar(df_dia, nome_arquivo)

            # Se DELETAR_APOS_PROCESSAR=True, processa as features e deleta o bruto
            if DELETAR_APOS_PROCESSAR:
                print(f"[main] ({i+1}/{len(dias)}) Processando features de {nome_dia}...")
                # Importa o features.py e processa este dia
                import features
                caminho_csv = os.path.join(PASTA_DADOS, f"{nome_arquivo}.csv")
                features_dia = features.processar_dia(caminho_csv)

                # Salva as features deste dia
                os.makedirs("data/processed", exist_ok=True)
                caminho_features = os.path.join("data/processed", f"features_{nome_dia}.csv")
                features_dia.to_csv(caminho_features)
                print(f"[main] Features salvas em {caminho_features}")

                # Deleta o CSV bruto para liberar disco
                deletar_arquivo(nome_arquivo)

    finally:
        # 4. Fecha a conexão (sempre, mesmo se houver erro)
        conn.close()
        print("[main] Conexão fechada.")

    # 5. Consolida todas as features em um único arquivo
    print("\n[main] Consolidando todas as features...")
    import glob
    arquivos_features = sorted(glob.glob("data/processed/features_*.csv"))
    # Excluir o arquivo consolidado anterior (se existir) para não duplicar
    arquivos_features = [f for f in arquivos_features if "todos_dias" not in f]
    if len(arquivos_features) > 0:
        todas_features = pd.concat([pd.read_csv(f) for f in arquivos_features])
        todas_features.to_csv("data/processed/features_todos_dias.csv", index=False)
        print(f"[main] {len(todas_features)} linhas consolidadas em features_todos_dias.csv")

    print("=" * 60)
    print("  EXTRAÇÃO CONCLUÍDA!")
    print("=" * 60)


# ============================================================
# Executa se o arquivo for chamado diretamente
# python extracao.py
# ============================================================
if __name__ == "__main__":
    main()