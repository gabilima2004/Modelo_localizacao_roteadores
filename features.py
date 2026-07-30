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
============================================================
"""

import pandas as pd

# ============================================================
# Carregar os dados (dados brutos em data/raw/)
# ============================================================
df_metrics = pd.read_csv("data/raw/metrics_2026-04-01.csv", parse_dates=["timestamp"])


# ============================================================
# FUNÇÃO 1: Calcular deltas (tráfego real por minuto)
# ============================================================
def calcular_deltas():
    """Calcula o tráfego real por minuto a partir dos bytes acumulados.

    Os bytes_up e bytes_down são contadores acumulados (desde que o
    roteador ligou). O tráfego real de cada minuto é a DIFERENÇA
    entre o valor atual e o anterior (diff).

    Quando o delta é negativo, o contador reiniciou (roteador desligou).
    Nesse caso, o tráfego real é o próprio valor (bytes_up desde o reinício).
    """
    # Extrair a hora do timestamp (0-23)
    df_metrics["hora"] = df_metrics["timestamp"].dt.hour

    # Calcular diff agrupado por device_mac
    # (cada device tem seu próprio contador, não pode misturar)
    df_metrics["delta_bytes_up"] = df_metrics.groupby("device_mac")["bytes_up"].diff()

    # Tratar reinício: se delta < 0, o contador reiniciou
    # O tráfego real é o próprio bytes_up (novo valor desde o reinício)
    df_metrics.loc[df_metrics["delta_bytes_up"] < 0, "delta_bytes_up"] = df_metrics["bytes_up"]

    # Mesma lógica para bytes_down
    df_metrics["delta_bytes_down"] = df_metrics.groupby("device_mac")["bytes_down"].diff()
    df_metrics.loc[df_metrics["delta_bytes_down"] < 0, "delta_bytes_down"] = df_metrics["bytes_down"]

    print(f"[calcular_deltas] Deltas calculados para {len(df_metrics)} linhas")


# ============================================================
# FUNÇÃO 2: Tráfego por roteador por hora
# ============================================================
def trafego_por_hora():
    """Agrupa os deltas por roteador + hora e soma.

    Retorna um DataFrame onde:
    - Índice: router_mac + hora
    - Colunas: delta_bytes_up, delta_bytes_down

    Este DataFrame é a BASE para todas as outras features.
    Todas as funções seguintes recebem este DataFrame como parâmetro.
    """
    trafego = df_metrics.groupby(["router_mac", "hora"])[["delta_bytes_up", "delta_bytes_down"]].sum()

    print(f"[trafego_por_hora] {len(trafego)} linhas (roteador × hora)")
    return trafego


# ============================================================
# FUNÇÃO 3: Tráfego comercial (8h-17h)
# ============================================================
def trafego_comercial(trafego):
    """Soma o tráfego das horas comerciais (8h-17h) para cada roteador.

    Recebe o DataFrame 'trafego' (resultado de trafego_por_hora)
    e filtra só as horas 8-17, depois soma por roteador.
    """
    # reset_index() transforma o índice (router_mac, hora) em colunas normais
    # Isso facilita filtrar por hora
    trafego_reset = trafego.reset_index()

    # Filtrar só as horas comerciais (8 a 17)
    comercial = trafego_reset[trafego_reset["hora"].isin(range(8, 18))]

    # Agrupar por roteador e somar
    comercial = comercial.groupby("router_mac")[["delta_bytes_up", "delta_bytes_down"]].sum()

    print(f"[trafego_comercial] {len(comercial)} roteadores")
    return comercial


# ============================================================
# FUNÇÃO 4: Tráfego residencial (18h-7h)
# ============================================================
def trafego_residencial(trafego):
    """Soma o tráfego das horas residenciais (18h-7h) para cada roteador.

    O período residencial é das 18h até as 7h (inclui madrugada).
    Isso significa hora >= 18 OU hora < 8.
    """
    trafego_reset = trafego.reset_index()

    # Filtrar horas residenciais: hora >= 18 OU hora < 8
    residencial = trafego_reset[
        (trafego_reset["hora"] >= 18) | (trafego_reset["hora"] < 8)
    ]

    # Agrupar por roteador e somar
    residencial = residencial.groupby("router_mac")[["delta_bytes_up", "delta_bytes_down"]].sum()

    print(f"[trafego_residencial] {len(residencial)} roteadores")
    return residencial


# ============================================================
# FUNÇÃO 5: Razão comercial (proporção do tráfego que é comercial)
# ============================================================
def razao_comercial(comercial, residencial):
    """Calcula a proporção do tráfego que é comercial.

    razao = trafego_comercial / (trafego_comercial + trafego_residencial)

    Se razao > 0.5 → a maioria do tráfego é comercial → provavelmente comercial
    Se razao < 0.5 → a maioria do tráfego é residencial → provavelmente residencial
    """
    # Somar up + down para ter o tráfego total de cada período
    total_comercial = comercial["delta_bytes_up"] + comercial["delta_bytes_down"]
    total_residencial = residencial["delta_bytes_up"] + residencial["delta_bytes_down"]

    # Razão = comercial / (comercial + residencial)
    razao = total_comercial / (total_comercial + total_residencial)

    print(f"[razao_comercial] {len(razao)} roteadores")
    return razao


# ============================================================
# FUNÇÃO 6: Hora de pico (hora de maior tráfego)
# ============================================================
def hora_pico(trafego):
    """Encontra a hora de maior tráfego (up + down) para cada roteador.

    Para cada roteador, qual hora teve o maior tráfego total?
    """
    # Somar up + down para ter o tráfego total por hora
    trafego_reset = trafego.reset_index()
    trafego_reset["trafego_total"] = (
        trafego_reset["delta_bytes_up"] + trafego_reset["delta_bytes_down"]
    )

    # Para cada roteador, achar a hora com maior tráfego_total
    # idxmax() retorna o ÍNDICE do maior valor
    pico = trafego_reset.groupby("router_mac")["trafego_total"].idxmax()

    # idxmax retorna o índice da linha (número), precisamos pegar a hora
    horas_pico = trafego_reset.loc[pico, ["router_mac", "hora"]].set_index("router_mac")["hora"]

    print(f"[hora_pico] {len(horas_pico)} roteadores")
    return horas_pico


# ============================================================
# FUNÇÃO 7: Perfil horário (24 valores por roteador)
# ============================================================
def perfil_horario(trafego):
    """Cria um perfil horário: 24 colunas (uma por hora) para cada roteador.

    Transforma o DataFrame de formato longo (router, hora, valor)
    para formato largo (router, h_0, h_1, ..., h_23).

    Isso é útil para o K-Means: cada roteador vira um ponto em
    um espaço de 24 dimensões.
    """
    # Somar up + down para ter o tráfego total por hora
    trafego_reset = trafego.reset_index()
    trafego_reset["trafego_total"] = (
        trafego_reset["delta_bytes_up"] + trafego_reset["delta_bytes_down"]
    )

    # pivot: transforma a coluna "hora" em 24 colunas (h_0, h_1, ..., h_23)
    perfil = trafego_reset.pivot_table(
        index="router_mac",      # cada linha = um roteador
        columns="hora",          # cada coluna = uma hora
        values="trafego_total",  # os valores = tráfego total
        fill_value=0             # se não tem dados para uma hora, preenche com 0
    )

    # Renomear as colunas para h_0, h_1, ..., h_23
    perfil.columns = [f"h_{int(h)}" for h in perfil.columns]

    print(f"[perfil_horario] {len(perfil)} roteadores × {len(perfil.columns)} horas")
    return perfil


# ============================================================
# FUNÇÃO PRINCIPAL: Junta tudo em uma tabela final
# ============================================================
def main():
    """Orquestra todas as funções e cria a tabela final de features.

    A tabela final tem 1 linha por roteador com todas as features:
    - trafego_comercial_up
    - trafego_comercial_down
    - trafego_residencial_up
    - trafego_residencial_down
    - razao_comercial
    - hora_pico
    - h_0, h_1, ..., h_23 (perfil horário)
    """
    print("=" * 60)
    print("  ENGENHARIA DE FEATURES — ETAPA 4")
    print("=" * 60)

    # 1. Calcular deltas (modifica df_metrics)
    print("\n→ Passo 1: Calculando deltas...")
    calcular_deltas()

    # 2. Agrupar por roteador + hora
    print("\n→ Passo 2: Agrupando por roteador + hora...")
    trafego = trafego_por_hora()

    # 3. Calcular tráfego comercial
    print("\n→ Passo 3: Calculando tráfego comercial (8h-17h)...")
    comercial = trafego_comercial(trafego)

    # 4. Calcular tráfego residencial
    print("\n→ Passo 4: Calculando tráfego residencial (18h-7h)...")
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

    # 8. Juntar tudo em uma tabela final
    print("\n→ Passo 8: Montando tabela final...")

    # Renomear colunas para evitar conflitos
    comercial.columns = ["trafego_comercial_up", "trafego_comercial_down"]
    residencial.columns = ["trafego_residencial_up", "trafego_residencial_down"]

    # Juntar tudo usando join (pelo índice router_mac)
    tabela = comercial.join(residencial)          # junta comercial + residencial
    tabela["razao_comercial"] = razao              # adiciona razão
    tabela["hora_pico"] = pico                     # adiciona hora de pico
    tabela = tabela.join(perfil)                   # adiciona perfil horário (24 colunas)

    print(f"\n✅ Tabela final: {len(tabela)} roteadores × {len(tabela.columns)} features")
    print(f"   Colunas: {list(tabela.columns)}")

    # 9. Filtrar roteadores com dados insuficientes
    # Roteadores com 20+ horas zeradas não têm informação suficiente
    # para classificar (só têm 4 horas ou menos de tráfego)
    print("\n→ Passo 9: Filtrando roteadores com dados insuficientes...")
    horas_zero = (tabela[[f"h_{i}" for i in range(24)]] == 0).sum(axis=1)
    print(f"   Roteadores com 24h zeradas: {(horas_zero == 24).sum()}")
    print(f"   Roteadores com 20+ horas zeradas: {(horas_zero >= 20).sum()}")

    # Manter só roteadores com menos de 20 horas zeradas
    tabela = tabela[horas_zero < 20]
    print(f"   Roteadores após filtro: {len(tabela)}")

    # Mostrar as primeiras linhas
    print("\n=== PRIMEIRAS 5 LINHAS ===")
    print(tabela.head())

    # Salvar em arquivo (dados processados em data/processed/)
    import os
    os.makedirs("data/processed", exist_ok=True)
    tabela.to_csv("data/processed/features_2026-04-01.csv")
    print(f"\n✅ Features salvas em data/processed/features_2026-04-01.csv")

    print("=" * 60)
    print("  ENGENHARIA DE FEATURES CONCLUÍDA!")
    print("=" * 60)

    return tabela


# ============================================================
# Executa se o arquivo for chamado diretamente
# python features.py
# ============================================================
if __name__ == "__main__":
    main()

