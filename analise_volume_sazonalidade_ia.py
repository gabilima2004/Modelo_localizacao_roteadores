"""
analise_volume_sazonalidade_ia.py — Análises Adicionais
============================================================

Analisa dois pontos críticos do modelo:
1. Prioridade 2: O K-Means está agrupando por volume ou por padrão?
2. Prioridade 4: A sazonalidade (mês a mês) afeta o comportamento?

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Configurar matplotlib para servidor sem GUI
import matplotlib
matplotlib.use("Agg")

# Configurações visuais
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["font.size"] = 11
CORES = {
    "comercial": "#e74c3c",      # vermelho
    "residencial": "#3498db",    # azul
    "padrao_anomalo": "#95a5a6", # cinza
}

PASTA_GRAFICOS = "data/processed/graficos"
os.makedirs(PASTA_GRAFICOS, exist_ok=True)

# ============================================================
# Carregar dados
# ============================================================
print("[analise] Carregando dados...")
df_classificacao = pd.read_csv(
    "data/processed/classificacao_ia_2026-04-01.csv",
    index_col="router_mac"
)

df_features = pd.read_csv("data/processed/features_todos_dias.csv")
print(f"[analise] Classificação: {len(df_classificacao)} roteadores")
print(f"[analise] Features: {len(df_features)} linhas (dias)")


# ============================================================
# PRIORIDADE 2: O K-Means agrupa por volume ou por padrão?
# ============================================================
def analisar_volume():
    """Verifica se o K-Means separou os grupos por volume total.

    Se o grupo residencial tiver volume muito maior que o comercial,
    o K-Means pode ter agrupado por volume (mesmo com normalização L1).
    """
    print(f"\n{'='*60}")
    print("  PRIORIDADE 2: Análise de Volume")
    print(f"{'='*60}")

    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]

    if not all(c in df_classificacao.columns for c in colunas_uteis):
        print("  Colunas uteis_h_* não encontradas — pulando")
        return

    # Calcular volume total (soma de todas as horas) para cada roteador
    df_classificacao["volume_uteis"] = df_classificacao[colunas_uteis].sum(axis=1) / 1e9  # GB
    df_classificacao["volume_fds"] = df_classificacao[colunas_fds].sum(axis=1) / 1e9
    df_classificacao["volume_total"] = df_classificacao["volume_uteis"] + df_classificacao["volume_fds"]

    # Comparar volume por grupo
    print("\n→ Volume médio por grupo (GB):")
    volume_por_grupo = df_classificacao.groupby("classificacao_kmeans")[
        ["volume_uteis", "volume_fds", "volume_total"]
    ].mean()
    print(volume_por_grupo.round(2))

    # Plotar boxplot do volume por grupo
    fig, ax = plt.subplots(figsize=(10, 6))
    dados = [
        df_classificacao[df_classificacao["classificacao_kmeans"] == "comercial"]["volume_total"],
        df_classificacao[df_classificacao["classificacao_kmeans"] == "residencial"]["volume_total"],
        df_classificacao[df_classificacao["classificacao_kmeans"] == "padrao_anomalo"]["volume_total"],
    ]
    labels = ["Comercial", "Residencial", "Padrão Anômalo"]
    cores = [CORES["comercial"], CORES["residencial"], CORES["padrao_anomalo"]]

    bp = ax.boxplot(dados, tick_labels=labels, patch_artist=True, showfliers=False)
    for patch, cor in zip(bp["boxes"], cores):
        patch.set_facecolor(cor)
        patch.set_alpha(0.7)

    ax.set_ylabel("Volume total (GB)", fontsize=12)
    ax.set_title("Distribuição de Volume Total por Grupo (K-Means)\nO K-Means agrupou por volume?",
                 fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    caminho = os.path.join(PASTA_GRAFICOS, "11_volume_por_grupo.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Gráfico salvo: {caminho}")

    # Conclusão
    vol_com = volume_por_grupo.loc["comercial", "volume_total"] if "comercial" in volume_por_grupo.index else 0
    vol_res = volume_por_grupo.loc["residencial", "volume_total"] if "residencial" in volume_por_grupo.index else 0

    print(f"\n→ Conclusão:")
    if vol_res > vol_com * 2:
        print(f"  ⚠️ O residencial ({vol_res:.1f} GB) tem MUITO mais volume que o comercial ({vol_com:.1f} GB).")
        print(f"     O K-Means pode estar influenciado pelo volume, mesmo com L1.")
        print(f"     Sugestão: testar outras normalizações (StandardScaler, RobustScaler).")
    else:
        print(f"  ✅ O volume do residencial ({vol_res:.1f} GB) e comercial ({vol_com:.1f} GB) são próximos.")
        print(f"     O K-Means provavelmente está agrupando pelo padrão (horário), não pelo volume.")


# ============================================================
# PRIORIDADE 4: Análise de Sazonalidade (Mês a Mês)
# ============================================================
def analisar_sazonalidade():
    """Verifica se o comportamento (razão comercial) muda entre meses.

    Se a razão comercial de um roteador muda muito entre abril e julho,
    significa que ele tem comportamento sazonal (ex: férias escolares).
    """
    print(f"\n{'='*60}")
    print("  PRIORIDADE 4: Análise de Sazonalidade")
    print(f"{'='*60}")

    if "mes" not in df_features.columns or "razao_comercial" not in df_features.columns:
        print("  Colunas 'mes' ou 'razao_comercial' não encontradas — pulando")
        return

    # 1. Razão comercial média por mês (geral)
    print("\n→ Razão comercial média por mês (todos os roteadores):")
    razao_por_mes = df_features.groupby("mes")["razao_comercial"].mean()
    print(razao_por_mes.round(4))

    # Plotar gráfico de linha
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(razao_por_mes.index, razao_por_mes.values, "o-", color="purple",
            linewidth=2, markersize=8)
    ax.set_xlabel("Mês", fontsize=12)
    ax.set_ylabel("Razão Comercial Média", fontsize=12)
    ax.set_title("Sazonalidade: Razão Comercial Média por Mês\nO comportamento muda entre meses?",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(razao_por_mes.index)
    ax.grid(True, alpha=0.3)

    caminho = os.path.join(PASTA_GRAFICOS, "12_sazonalidade_razao_mes.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Gráfico salvo: {caminho}")

    # 2. Variabilidade da razão comercial por roteador
    print("\n→ Variabilidade da razão comercial por roteador (entre meses):")
    variabilidade = df_features.groupby("router_mac")["razao_comercial"].std()
    print(f"  Média do desvio padrão: {variabilidade.mean():.4f}")
    print(f"  Máximo desvio padrão: {variabilidade.max():.4f}")
    print(f"  Roteadores com alta variabilidade (std > 0.1): {(variabilidade > 0.1).sum()}")

    # 3. Top 10 roteadores mais sazonais (que mais mudam entre meses)
    top_sazonais = variabilidade.nlargest(10)
    print(f"\n→ Top 10 roteadores mais sazonais (maior variação entre meses):")
    print(top_sazonais.round(4))

    # Plotar a variação desses roteadores
    fig, ax = plt.subplots(figsize=(12, 6))
    for mac in top_sazonais.index:
        dados_router = df_features[df_features["router_mac"] == mac].groupby("mes")["razao_comercial"].mean()
        ax.plot(dados_router.index, dados_router.values, "o-", label=mac, linewidth=1.5, markersize=5)

    ax.set_xlabel("Mês", fontsize=12)
    ax.set_ylabel("Razão Comercial", fontsize=12)
    ax.set_title("Top 10 Roteadores Mais Sazonais\n(Razão Comercial por Mês)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(razao_por_mes.index)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)

    caminho = os.path.join(PASTA_GRAFICOS, "13_top_sazonais.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ Gráfico salvo: {caminho}")

    # Conclusão
    print(f"\n→ Conclusão:")
    if variabilidade.mean() > 0.1:
        print(f"  ⚠️ Alta variabilidade entre meses (média std = {variabilidade.mean():.4f}).")
        print(f"     A sazonalidade afeta o comportamento. O modelo atual (média de tudo) pode estar")
        print(f"     diluindo padrões importantes. Considere classificar por mês ou usar votação.")
    else:
        print(f"  ✅ Baixa variabilidade entre meses (média std = {variabilidade.mean():.4f}).")
        print(f"     O comportamento é estável. Fazer a média de todos os meses é seguro.")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    print("=" * 60)
    print("  ANÁLISE DE VOLUME E SAZONALIDADE")
    print("=" * 60)

    analisar_volume()
    analisar_sazonalidade()

    print(f"\n{'='*60}")
    print("  ANÁLISES CONCLUÍDAS!")
    print(f"{'='*60}")
    print(f"  Gráficos salvos em: {PASTA_GRAFICOS}/")
    print(f"  (arquivos 11, 12 e 13)")


if __name__ == "__main__":
    main()