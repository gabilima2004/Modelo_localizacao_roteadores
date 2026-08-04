"""
graficos_ia.py — Geração de Gráficos para Visualização
============================================================
Gera gráficos PNG para visualizar os resultados do modelo.

Gráficos gerados:
  1. Distribuição pela regra (pizza)
  2. Distribuição pelo K-Means (pizza)
  3. Concordância regra vs K-Means (barras)
  4. Perfil horário comercial — úteis vs fds (linha)
  5. Volume comercial — úteis vs fds (barras)
  6. Perfil horário residencial — úteis vs fds (linha)
  7. Volume residencial — úteis vs fds (barras)
  8. Comercial vs residencial por cidade (barras empilhadas)
  9. Silhouette Score por K (cotovelo) — sugestão extra
  10. Histograma da razão comercial — sugestão extra

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Configurar matplotlib para não precisar de display (servidor sem GUI)
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

# ============================================================
# Carregar dados
# ============================================================
df = pd.read_csv(
    "data/processed/classificacao_ia_2026-04-01.csv",
    index_col="router_mac"
)
print(f"[graficos] Carregado: {len(df)} roteadores")

# Criar pasta para gráficos
PASTA_GRAFICOS = "data/processed/graficos"
os.makedirs(PASTA_GRAFICOS, exist_ok=True)


def salvar_grafico(fig, nome):
    """Salva um gráfico PNG na pasta de gráficos."""
    caminho = os.path.join(PASTA_GRAFICOS, f"{nome}.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {caminho}")


# ============================================================
# GRÁFICO 1: Distribuição pela regra (pizza)
# ============================================================
def grafico_distribuicao_regra():
    """Pizza mostrando a distribuição da classificação pela regra."""
    print("\n→ Gráfico 1: Distribuição pela regra")
    counts = df["classificacao_regra"].value_counts()

    fig, ax = plt.subplots()
    cores = [CORES.get(c, "#2ecc71") for c in counts.index]
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%",
           colors=cores, startangle=90)
    ax.set_title("Distribuição pela Regra de Negócio", fontsize=14, fontweight="bold")
    salvar_grafico(fig, "01_distribuicao_regra")


# ============================================================
# GRÁFICO 2: Distribuição pelo K-Means (pizza)
# ============================================================
def grafico_distribuicao_kmeans():
    """Pizza mostrando a distribuição da classificação pelo K-Means."""
    print("\n→ Gráfico 2: Distribuição pelo K-Means")
    counts = df["classificacao_kmeans"].value_counts()

    fig, ax = plt.subplots()
    cores = [CORES.get(c, "#2ecc71") for c in counts.index]
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%",
           colors=cores, startangle=90)
    ax.set_title("Distribuição pelo K-Means", fontsize=14, fontweight="bold")
    salvar_grafico(fig, "02_distribuicao_kmeans")


# ============================================================
# GRÁFICO 3: Concordância regra vs K-Means (barras)
# ============================================================
def grafico_concordancia():
    """Barras mostrando concordância e discordância entre os métodos."""
    print("\n→ Gráfico 3: Concordância regra vs K-Means")
    concordam = (df["classificacao_regra"] == df["classificacao_kmeans"]).sum()
    discordam = (df["classificacao_regra"] != df["classificacao_kmeans"]).sum()

    fig, ax = plt.subplots()
    categorias = ["Concordam", "Discordam"]
    valores = [concordam, discordam]
    cores = ["#2ecc71", "#e74c3c"]
    bars = ax.bar(categorias, valores, color=cores, edgecolor="black")

    # Adicionar valores nas barras
    for bar, val in zip(bars, valores):
        pct = val / len(df) * 100
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                f"{val}\n({pct:.1f}%)", ha="center", va="bottom", fontweight="bold")

    ax.set_ylabel("Quantidade de roteadores")
    ax.set_title("Concordância: Regra vs K-Means", fontsize=14, fontweight="bold")
    salvar_grafico(fig, "03_concordancia")


# ============================================================
# GRÁFICO 4: Perfil horário — comercial e residencial juntos
# ============================================================
def grafico_perfil_horario_comparativo():
    """Perfil horário médio: comercial vs residencial, úteis vs fds.

    Mostra os 4 perfis no mesmo gráfico para comparação direta:
    - Comercial em dias úteis (vermelho sólido)
    - Comercial em fds (vermelho tracejado)
    - Residencial em dias úteis (azul sólido)
    - Residencial em fds (azul tracejado)
    """
    print("\n→ Gráfico 4: Perfil horário comparativo (comercial vs residencial)")

    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]

    if not all(c in df.columns for c in colunas_uteis):
        print("  Colunas uteis_h_* não encontradas — pulando")
        return

    # Separar por classificação
    comerciais = df[df["classificacao_kmeans"] == "comercial"]
    residenciais = df[df["classificacao_kmeans"] == "residencial"]

    # Calcular médias
    com_uteis = comerciais[colunas_uteis].mean()
    com_fds = comerciais[colunas_fds].mean()
    res_uteis = residenciais[colunas_uteis].mean()
    res_fds = residenciais[colunas_fds].mean()

    horas = list(range(24))

    fig, ax = plt.subplots(figsize=(12, 6))

    # Comercial: vermelho
    ax.plot(horas, com_uteis, "o-", color=CORES["comercial"],
            label="Comercial — dias úteis", linewidth=2.5, markersize=6)
    ax.plot(horas, com_fds, "s--", color=CORES["comercial"],
            label="Comercial — fins de semana", linewidth=2, markersize=5, alpha=0.7)

    # Residencial: azul
    ax.plot(horas, res_uteis, "o-", color=CORES["residencial"],
            label="Residencial — dias úteis", linewidth=2.5, markersize=6)
    ax.plot(horas, res_fds, "s--", color=CORES["residencial"],
            label="Residencial — fins de semana", linewidth=2, markersize=5, alpha=0.7)

    # Destacar horário comercial
    ax.axvspan(8, 18, alpha=0.08, color="orange")
    ax.text(13, ax.get_ylim()[1]*0.95, "Horário comercial", ha="center",
            fontsize=9, color="orange", alpha=0.8)

    ax.set_xlabel("Hora do dia", fontsize=12)
    ax.set_ylabel("Tráfego médio (bytes)", fontsize=12)
    ax.set_title("Perfil Horário: Comercial vs Residencial\nDias Úteis vs Fins de Semana",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(horas)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    salvar_grafico(fig, "04_perfil_horario_comparativo")


# ============================================================
# GRÁFICO 5: Volume médio por hora — comercial vs residencial
# ============================================================
def grafico_volume_por_hora():
    """Volume médio por hora: barras agrupadas (comercial vs residencial).

    Em vez de histograma (que não deu insight), mostra o volume médio
    por hora em barras, comparando comercial e residencial.
    """
    print("\n→ Gráfico 5: Volume médio por hora (comercial vs residencial)")

    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]

    if not all(c in df.columns for c in colunas_uteis):
        print("  Colunas uteis_h_* não encontradas — pulando")
        return

    comerciais = df[df["classificacao_kmeans"] == "comercial"]
    residenciais = df[df["classificacao_kmeans"] == "residencial"]

    # Volume médio por hora (em GB) — dias úteis
    vol_com = comerciais[colunas_uteis].mean() / 1e9
    vol_res = residenciais[colunas_uteis].mean() / 1e9

    horas = list(range(24))
    x = np.arange(len(horas))
    largura = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - largura/2, vol_com, largura, label="Comercial",
                  color=CORES["comercial"], edgecolor="black", alpha=0.8)
    bars2 = ax.bar(x + largura/2, vol_res, largura, label="Residencial",
                  color=CORES["residencial"], edgecolor="black", alpha=0.8)

    # Destacar horário comercial
    ax.axvspan(7.5, 17.5, alpha=0.08, color="orange")
    ax.text(12.5, ax.get_ylim()[1]*0.95, "Horário comercial", ha="center",
            fontsize=9, color="orange", alpha=0.8)

    ax.set_xlabel("Hora do dia", fontsize=12)
    ax.set_ylabel("Volume médio (GB)", fontsize=12)
    ax.set_title("Volume Médio por Hora (Dias Úteis)\nComercial vs Residencial",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(horas)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")
    salvar_grafico(fig, "05_volume_por_hora")


# ============================================================
# GRÁFICO 6: Volume total — úteis vs fds (boxplot)
# ============================================================
def grafico_volume_total_boxplot():
    """Boxplot do volume total: comercial vs residencial, úteis vs fds.

    Boxplot mostra mediana, quartis e outliers — muito mais
    informativo que histograma para comparar distribuições.
    """
    print("\n→ Gráfico 6: Volume total (boxplot: comercial vs residencial)")

    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]

    if not all(c in df.columns for c in colunas_uteis):
        print("  Colunas uteis_h_* não encontradas — pulando")
        return

    comerciais = df[df["classificacao_kmeans"] == "comercial"]
    residenciais = df[df["classificacao_kmeans"] == "residencial"]

    # Volume total por roteador (em GB)
    dados = [
        comerciais[colunas_uteis].sum(axis=1) / 1e9,
        comerciais[colunas_fds].sum(axis=1) / 1e9,
        residenciais[colunas_uteis].sum(axis=1) / 1e9,
        residenciais[colunas_fds].sum(axis=1) / 1e9,
    ]
    labels = ["Comercial\núteis", "Comercial\nfds", "Residencial\núteis", "Residencial\nfds"]
    cores = [CORES["comercial"], CORES["comercial"], CORES["residencial"], CORES["residencial"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(dados, tick_labels=labels, patch_artist=True, showfliers=False)

    # Colorir as caixas
    for patch, cor in zip(bp["boxes"], cores):
        patch.set_facecolor(cor)
        patch.set_alpha(0.7)

    ax.set_ylabel("Volume total (GB)", fontsize=12)
    ax.set_title("Distribuição de Volume Total\nComercial vs Residencial, Úteis vs Fds",
                 fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    salvar_grafico(fig, "06_volume_boxplot")


# ============================================================
# GRÁFICO 8: Comercial vs residencial por cidade (barras empilhadas)
# ============================================================
def grafico_por_cidade():
    """Barras empilhadas mostrando comercial vs residencial por cidade."""
    print("\n→ Gráfico 8: Comercial vs residencial por cidade")

    # Carregar localização
    routers = pd.read_csv("data/raw/routers.csv", parse_dates=["timestamp"])
    routers = routers.sort_values("timestamp", ascending=False).drop_duplicates(
        "router_mac", keep="first"
    ).set_index("router_mac")

    # Juntar
    df_loc = df.join(routers[["city"]], how="inner")
    df_loc = df_loc.dropna(subset=["city"])

    # Contar por cidade e classificação
    tabela = pd.crosstab(df_loc["city"], df_loc["classificacao_kmeans"])

    # Ordenar por total (maior para menor)
    tabela = tabela.loc[tabela.sum(axis=1).sort_values(ascending=True).index]

    fig, ax = plt.subplots(figsize=(12, 7))
    tabela.plot(kind="barh", stacked=True, ax=ax,
                color=[CORES.get(c, "#2ecc71") for c in tabela.columns],
                edgecolor="black", width=0.7)

    ax.set_xlabel("Quantidade de roteadores")
    ax.set_ylabel("Cidade")
    ax.set_title("Comercial vs Residencial por Cidade (K-Means)",
                 fontsize=14, fontweight="bold")
    ax.legend(title="Classificação", loc="lower right")
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    salvar_grafico(fig, "08_por_cidade")


# ============================================================
# GRÁFICO 9 (SUGESTÃO): Histograma da razão comercial
# ============================================================
def grafico_histograma_razao():
    """Histograma da razão comercial, colorido por classificação K-Means."""
    print("\n→ Gráfico 9: Histograma da razão comercial (sugestão)")

    fig, ax = plt.subplots()

    # Plotar cada classe com cor diferente
    for classe, cor in CORES.items():
        dados = df[df["classificacao_kmeans"] == classe]["razao_comercial"]
        if len(dados) > 0:
            ax.hist(dados, bins=30, alpha=0.7, label=classe,
                    color=cor, edgecolor="black")

    # Linha vertical no 0.5 (limiar da regra)
    ax.axvline(0.5, color="black", linestyle="--", linewidth=2,
               label="Limiar da regra (0.5)")

    ax.set_xlabel("Razão comercial")
    ax.set_ylabel("Quantidade de roteadores")
    ax.set_title("Histograma da Razão Comercial por Classificação (K-Means)",
                 fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    salvar_grafico(fig, "09_histograma_razao")


# ============================================================
# GRÁFICO 10 (SUGESTÃO): Comparação regra vs K-Means (scatter)
# ============================================================
def grafico_scatter_razao():
    """Scatter plot comparando razão comercial com hora de pico."""
    print("\n→ Gráfico 10: Scatter razão comercial vs hora de pico (sugestão)")

    fig, ax = plt.subplots()

    for classe, cor in CORES.items():
        dados = df[df["classificacao_kmeans"] == classe]
        if len(dados) > 0:
            ax.scatter(dados["hora_pico"], dados["razao_comercial"],
                       alpha=0.3, s=10, label=classe, color=cor)

    ax.axvline(8, color="orange", linestyle=":", alpha=0.5)
    ax.axvline(18, color="orange", linestyle=":", alpha=0.5, label="Horário comercial")
    ax.axhline(0.5, color="black", linestyle="--", alpha=0.5, label="Limiar regra (0.5)")

    ax.set_xlabel("Hora de pico")
    ax.set_ylabel("Razão comercial")
    ax.set_title("Hora de Pico vs Razão Comercial (K-Means)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    ax.grid(True, alpha=0.3)
    salvar_grafico(fig, "10_scatter_razao_pico")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    """Gera todos os gráficos."""
    print("=" * 60)
    print("  GERAÇÃO DE GRÁFICOS")
    print("=" * 60)

    # Verificar se matplotlib está instalado
    try:
        import matplotlib
    except ImportError:
        print("❌ matplotlib não instalado. Instale com: pip install matplotlib")
        return

    # Gerar todos os gráficos
    grafico_distribuicao_regra()
    grafico_distribuicao_kmeans()
    grafico_concordancia()
    grafico_perfil_horario_comparativo()
    grafico_volume_por_hora()
    grafico_volume_total_boxplot()
    grafico_por_cidade()
    grafico_histograma_razao()
    grafico_scatter_razao()

    print(f"\n{'='*60}")
    print("  GRÁFICOS CONCLUÍDOS!")
    print(f"{'='*60}")
    print(f"  Os arquivos PNG estão em: {PASTA_GRAFICOS}/")
    print(f"  Abra-os no VS Code para visualizar!")


# ============================================================
# Executa se o arquivo for chamado diretamente
# python graficos_ia.py
# ============================================================
if __name__ == "__main__":
    main()