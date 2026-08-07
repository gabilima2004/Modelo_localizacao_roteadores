"""
features.py — Engenharia de Features
============================================================
ETAPA 4 DO PROJETO
============================================================

Transforma os dados brutos (bytes acumulados por minuto) em
features úteis para o modelo (tráfego por hora, por período,
hora de pico, perfil horário).

FLUXO:
  1. calcular_deltas()        → tráfego real por minuto
  2. trafego_por_hora()       → tráfego por roteador por hora
  3. trafego_comercial()      → tráfego das 8h-17h por roteador
  4. trafego_residencial()    → tráfego das 18h-7h por roteador
  5. razao_comercial()        → proporção do tráfego comercial
  6. hora_pico()              → hora de maior tráfego por roteador
  7. perfil_horario()         → 24 valores de tráfego por roteador
  8. main()                   → junta tudo em uma tabela final

MÚLTIPLOS DIAS:
  Este script processa TODOS os dias encontrados na pasta data/raw/
  (arquivos metrics_YYYY-MM-DD.csv). Para cada dia:
  1. Carrega o CSV
  2. Calcula as features
  3. Adiciona coluna 'data' e 'dia_semana' (0=segunda, 6=domingo)
  4. Acumula no resultado final
  5. Salva tudo em data/processed/features_todos_dias.csv

  Isso permite analisar dias úteis vs fins de semana separadamente.
============================================================
"""

import pandas as pd
import os
import glob

try:
    import holidays
    FERIADOS = holidays.Brazil(state="RJ")
except ImportError:
    print("[features] Biblioteca 'holidays' não instalada — feriados não serão considerados")
    FERIADOS = None

# ============================================================
# Configurações
# ============================================================
PASTA_RAW = "data/raw"
PASTA_PROCESSED = "data/processed"


# ============================================================
# FUNÇÃO 1: Calcular deltas (tráfego real por minuto)
# ============================================================
def calcular_deltas(df_metrics):
    """Calcula o tráfego real por minuto a partir dos bytes acumulados.

    Recebe o DataFrame como parâmetro (em vez de usar variável global).
    """
    # Extrair a hora do timestamp (0-23)
    df_metrics["hora"] = df_metrics["timestamp"].dt.hour

    # Calcular diff agrupado por device_mac
    df_metrics["delta_bytes_up"] = df_metrics.groupby("device_mac")["bytes_up"].diff()

    # Tratar reinício: se delta < 0, o contador reiniciou
    df_metrics.loc[df_metrics["delta_bytes_up"] < 0, "delta_bytes_up"] = df_metrics["bytes_up"]

    # Mesma lógica para bytes_down
    df_metrics["delta_bytes_down"] = df_metrics.groupby("device_mac")["bytes_down"].diff()
    df_metrics.loc[df_metrics["delta_bytes_down"] < 0, "delta_bytes_down"] = df_metrics["bytes_down"]

    print(f"[calcular_deltas] Deltas calculados para {len(df_metrics)} linhas")
    return df_metrics


# ============================================================
# FUNÇÃO 2: Tráfego por roteador por hora
# ============================================================
def trafego_por_hora(df_metrics):
    """Agrupa os deltas por roteador + hora e soma.

    Mantém a coluna 'eh_fds' para que as funções de tráfego
    comercial e residencial possam filtrar só dias úteis.
    """
    # Agrupar por roteador + hora + eh_fds (para manter a info)
    trafego = df_metrics.groupby(["router_mac", "hora", "eh_fds"])[["delta_bytes_up", "delta_bytes_down"]].sum()
    print(f"[trafego_por_hora] {len(trafego)} linhas (roteador × hora × tipo_dia)")
    return trafego


# ============================================================
# FUNÇÃO 3: Tráfego comercial (8h-17h) — SÓ em dias úteis
# ============================================================
def trafego_comercial(trafego, eh_fds=False):
    """Soma o tráfego das horas comerciais (8h-17h) para cada roteador.

    IMPORTANTE: só considera dias úteis (eh_fds=False).
    Fins de semana e feriados têm comportamento diferente (comércio fecha)
    e não devem entrar no cálculo do tráfego comercial.
    """
    trafego_reset = trafego.reset_index()

    # Filtrar só dias úteis (eh_fds=False) E horas comerciais (8-17)
    comercial = trafego_reset[
        (trafego_reset["eh_fds"] == False) &
        (trafego_reset["hora"].isin(range(8, 18)))
    ]
    comercial = comercial.groupby("router_mac")[["delta_bytes_up", "delta_bytes_down"]].sum()
    print(f"[trafego_comercial] {len(comercial)} roteadores (só dias úteis)")
    return comercial


# ============================================================
# FUNÇÃO 4: Tráfego residencial (18h-7h) — SÓ em dias úteis
# ============================================================
def trafego_residencial(trafego, eh_fds=False):
    """Soma o tráfego das horas residenciais (18h-7h) para cada roteador.

    IMPORTANTE: só considera dias úteis (eh_fds=False).
    A razão comercial compara o comportamento DURANTE a semana.
    """
    trafego_reset = trafego.reset_index()

    # Filtrar só dias úteis (eh_fds=False) E horas residenciais (18-7)
    residencial = trafego_reset[
        (trafego_reset["eh_fds"] == False) &
        ((trafego_reset["hora"] >= 18) | (trafego_reset["hora"] < 8))
    ]
    residencial = residencial.groupby("router_mac")[["delta_bytes_up", "delta_bytes_down"]].sum()
    print(f"[trafego_residencial] {len(residencial)} roteadores (só dias úteis)")
    return residencial


# ============================================================
# FUNÇÃO 5: Razão comercial
# ============================================================
def razao_comercial(comercial, residencial):
    """Calcula a proporção do tráfego que é comercial."""
    total_comercial = comercial["delta_bytes_up"] + comercial["delta_bytes_down"]
    total_residencial = residencial["delta_bytes_up"] + residencial["delta_bytes_down"]
    razao = total_comercial / (total_comercial + total_residencial)
    print(f"[razao_comercial] {len(razao)} roteadores")
    return razao


# ============================================================
# FUNÇÃO 6: Hora de pico
# ============================================================
def hora_pico(trafego):
    """Encontra a hora de maior tráfego para cada roteador."""
    trafego_reset = trafego.reset_index()
    trafego_reset["trafego_total"] = (
        trafego_reset["delta_bytes_up"] + trafego_reset["delta_bytes_down"]
    )
    pico = trafego_reset.groupby("router_mac")["trafego_total"].idxmax()
    horas_pico = trafego_reset.loc[pico, ["router_mac", "hora"]].set_index("router_mac")["hora"]
    print(f"[hora_pico] {len(horas_pico)} roteadores")
    return horas_pico


# ============================================================
# FUNÇÃO 7: Perfil horário (24 valores por roteador)
# ============================================================
def perfil_horario(trafego):
    """Cria um perfil horário: 24 colunas para cada roteador.

    Garante que SEMPRE existam 24 colunas (h_0 a h_23), mesmo se
    algumas horas não tiverem dados (preenchidas com zero).
    Isso evita erros quando um dia tem dados de poucas horas.
    """
    trafego_reset = trafego.reset_index()
    trafego_reset["trafego_total"] = (
        trafego_reset["delta_bytes_up"] + trafego_reset["delta_bytes_down"]
    )
    perfil = trafego_reset.pivot_table(
        index="router_mac",
        columns="hora",
        values="trafego_total",
        fill_value=0
    )

    # GARANTIR 24 COLUNAS (h_0 a h_23)
    # Se um dia tem dados de poucas horas, o pivot cria só algumas colunas.
    # Reindex adiciona as horas que faltam, preenchidas com zero.
    todas_horas = list(range(24))
    perfil = perfil.reindex(columns=todas_horas, fill_value=0)

    # Renomear as colunas para h_0, h_1, ..., h_23
    perfil.columns = [f"h_{int(h)}" for h in perfil.columns]

    print(f"[perfil_horario] {len(perfil)} roteadores × {len(perfil.columns)} horas")
    return perfil


# ============================================================
# FUNÇÃO 8: Processar um único dia
# ============================================================
def processar_dia(caminho_csv):
    """Processa um único arquivo de métricas e retorna as features.

    Parâmetros:
        caminho_csv: caminho para o arquivo metrics_YYYY-MM-DD.csv

    Retorna:
        DataFrame com as features do dia (1 linha por roteador)
    """
    # Extrair a data do nome do arquivo (metrics_2026-04-01.csv → 2026-04-01)
    nome_arquivo = os.path.basename(caminho_csv)
    data_str = nome_arquivo.replace("metrics_", "").replace(".csv", "")
    data = pd.Timestamp(data_str)

    # 0 = segunda, 6 = domingo
    dia_semana = data.dayofweek

    # Verificar se é feriado (nacional ou estadual do RJ)
    eh_feriado = FERIADOS is not None and data in FERIADOS

    # eh_fds = True se sábado, domingo OU feriado
    # Feriados têm comportamento de fim de semana (comércio fecha)
    eh_fds = (dia_semana >= 5) or eh_feriado

    if eh_feriado:
        print(f"  → {data_str} é feriado! Tratando como não útil")

    print(f"\n{'='*60}")
    print(f"  Processando dia {data_str} ({['seg','ter','qua','qui','sex','sab','dom'][dia_semana]})")
    print(f"{'='*60}")

    # Carregar os dados
    df_metrics = pd.read_csv(caminho_csv, parse_dates=["timestamp"])
    print(f"→ Carregado: {len(df_metrics)} linhas")

    # Adicionar coluna eh_fds no df_metrics (antes de calcular_deltas)
    # para que trafego_por_hora possa agrupar por tipo de dia
    df_metrics["eh_fds"] = eh_fds

    # 1. Calcular deltas
    print("\n→ Passo 1: Calculando deltas...")
    df_metrics = calcular_deltas(df_metrics)

    # 2. Agrupar por roteador + hora + tipo de dia
    print("\n→ Passo 2: Agrupando por roteador + hora...")
    trafego = trafego_por_hora(df_metrics)

    # 3. Calcular tráfego comercial (só dias úteis)
    print("\n→ Passo 3: Calculando tráfego comercial (8h-17h, só dias úteis)...")
    comercial = trafego_comercial(trafego)

    # 4. Calcular tráfego residencial (só dias úteis)
    print("\n→ Passo 4: Calculando tráfego residencial (18h-7h, só dias úteis)...")
    residencial = trafego_residencial(trafego)

    # 5. Calcular razão comercial
    print("\n→ Passo 5: Calculando razão comercial...")
    razao = razao_comercial(comercial, residencial)

    # 6. Calcular hora de pico
    print("\n→ Passo 6: Calculando hora de pico...")
    pico = hora_pico(trafego)

    # 7. Calcular perfil horário
    print("\n→ Passo 7: Calculando perfil horário (24 valores)...")
    perfil = perfil_horario(trafego)

    # 8. Montar tabela do dia
    print("\n→ Passo 8: Montando tabela do dia...")
    comercial.columns = ["trafego_comercial_up", "trafego_comercial_down"]
    residencial.columns = ["trafego_residencial_up", "trafego_residencial_down"]

    tabela = comercial.join(residencial)
    tabela["razao_comercial"] = razao
    tabela["hora_pico"] = pico
    tabela = tabela.join(perfil)

    # Adicionar colunas de data e dia da semana
    tabela["data"] = data_str
    tabela["dia_semana"] = dia_semana  # 0=segunda, 6=domingo
    tabela["eh_fds"] = eh_fds           # True se sábado, domingo ou feriado
    tabela["eh_feriado"] = eh_feriado   # True se feriado (nacional ou estadual)
    tabela["mes"] = data.month          # 1-12 (para análise sazonal)

    # 9. Filtrar roteadores com dados insuficientes
    print("\n→ Passo 9: Filtrando roteadores com dados insuficientes...")
    horas_zero = (tabela[[f"h_{i}" for i in range(24)]] == 0).sum(axis=1)
    tabela = tabela[horas_zero < 20]
    print(f"   Roteadores após filtro: {len(tabela)}")

    # Libera memória (df_metrics não é mais necessário)
    del df_metrics

    return tabela


# ============================================================
# FUNÇÃO PRINCIPAL: Processa todos os dias e junta tudo
# ============================================================
def main():
    """Processa todos os arquivos de métricas na pasta data/raw/.

    Para cada arquivo metrics_YYYY-MM-DD.csv:
    1. Carrega os dados
    2. Calcula as features
    3. Adiciona colunas 'data', 'dia_semana' e 'eh_fds'
    4. Acumula no resultado final

    No final, salva tudo em data/processed/features_todos_dias.csv
    """
    print("=" * 60)
    print("  ENGENHARIA DE FEATURES — ETAPA 4")
    print("=" * 60)

    # Encontrar todos os arquivos de métricas na pasta data/raw/
    arquivos = sorted(glob.glob(os.path.join(PASTA_RAW, "metrics_*.csv")))
    print(f"\n→ Encontrados {len(arquivos)} arquivos de métricas")

    if len(arquivos) == 0:
        print("❌ Nenhum arquivo encontrado em data/raw/")
        print("   Rode o extracao.py primeiro!")
        return

    # Processar cada dia e acumular
    todas_features = []

    for i, caminho in enumerate(arquivos):
        print(f"\n→ Processando arquivo {i+1}/{len(arquivos)}...")
        try:
            features_dia = processar_dia(caminho)
            todas_features.append(features_dia)
            print(f"   ✅ {len(features_dia)} roteadores processados")
        except Exception as e:
            print(f"   ❌ Erro ao processar {caminho}: {e}")
            continue

    # Juntar todos os dias
    print(f"\n{'='*60}")
    print("  Juntando todos os dias...")
    print(f"{'='*60}")

    tabela_final = pd.concat(todas_features)
    print(f"✅ Tabela final: {len(tabela_final)} linhas × {len(tabela_final.columns)} colunas")
    print(f"   Dias processados: {tabela_final['data'].nunique()}")
    print(f"   Roteadores únicos: {tabela_final.index.nunique()}")

    # Mostrar distribuição por dia da semana
    print(f"\n→ Distribuição por dia da semana:")
    dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    for d in range(7):
        qtd = (tabela_final['dia_semana'] == d).sum()
        print(f"   {dias[d]}: {qtd} roteadores-dia")

    # Salvar
    os.makedirs(PASTA_PROCESSED, exist_ok=True)
    caminho_saida = os.path.join(PASTA_PROCESSED, "features_todos_dias.csv")
    tabela_final.to_csv(caminho_saida)
    print(f"\n✅ Features salvas em {caminho_saida}")

    print(f"\n{'='*60}")
    print("  ENGENHARIA DE FEATURES CONCLUÍDA!")
    print(f"{'='*60}")

    return tabela_final


# ============================================================
# Executa se o arquivo for chamado diretamente
# python features.py
# ============================================================
if __name__ == "__main__":
    main()

