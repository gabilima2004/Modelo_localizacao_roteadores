"""
avaliacao_ia.py — Avaliação (Etapa 6)
============================================================
ETAPA 6 DO PROJETO: AVALIAÇÃO
============================================================

Valida as classificações do modelo cruzando com a localização
real dos roteadores (tabela routers).

Estratégias de validação:
  1. Amostra manual: olhar endereços de roteadores classificados
  2. Distribuição por cidade: comercial vs residencial por cidade
  3. Mapa: plotar roteadores no mapa coloridos por classificação
  4. Estatísticas: razão comercial média por cidade

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import os

# ============================================================
# Carregar dados
# ============================================================
# Classificação (resultado do modelo)
classificacao = pd.read_csv(
    "data/processed/classificacao_ia_2026-04-01.csv",
    index_col="router_mac"
)
print(f"[avaliacao] Classificação: {len(classificacao)} roteadores")

# Localização (tabela routers)
routers = pd.read_csv("data/raw/routers.csv", parse_dates=["timestamp"])
# Deduplicar pegando a versão mais recente
routers = routers.sort_values("timestamp", ascending=False).drop_duplicates(
    "router_mac", keep="first"
)
routers = routers.set_index("router_mac")
print(f"[avaliacao] Routers: {len(routers)} roteadores com localização")


# ============================================================
# FUNÇÃO 1: Juntar classificação com localização
# ============================================================
def juntar_dados():
    """Junta a classificação com a localização dos roteadores.

    Só mantém roteadores que têm AMBOS:
    - Classificação (do modelo)
    - Localização (da tabela routers)
    """
    # Selecionar colunas de localização
    colunas_loc = ["location", "city", "state", "latitude", "longitude"]
    colunas_loc = [c for c in colunas_loc if c in routers.columns]

    # Juntar (inner join: só roteadores que existem nos dois)
    df = classificacao.join(routers[colunas_loc], how="inner")

    print(f"\n[avaliacao] Roteadores com classificação E localização: {len(df)}")
    print(f"[avaliacao]   ({len(df)/len(classificacao)*100:.1f}% do total)")

    return df


# ============================================================
# FUNÇÃO 2: Amostra manual — olhar endereços
# ============================================================
def amostra_manual(df, n=10):
    """Mostra uma amostra de roteadores para validação visual.

    Você olha os endereços e verifica se a classificação faz sentido:
    - Roteador "comercial" deveria estar em zona comercial
    - Roteador "residencial" deveria estar em zona residencial
    """
    # Filtrar só roteadores que TÊM endereço (location não nulo)
    df_com_endereco = df.dropna(subset=["location"])

    print(f"\n{'='*60}")
    print("  AMOSTRA MANUAL — COMERCIAL")
    print(f"{'='*60}")

    # Pegar n roteadores classificados como comercial (pelo K-Means)
    comerciais = df_com_endereco[df_com_endereco["classificacao_kmeans"] == "comercial"]
    if len(comerciais) > 0:
        amostra = comerciais.sample(min(n, len(comerciais)))
        for mac, row in amostra.iterrows():
            loc = row.get("location", "sem endereço")
            city = row.get("city", "sem cidade")
            razao = row.get("razao_comercial", 0)
            print(f"  {mac}")
            print(f"    Endereço: {loc}")
            print(f"    Cidade: {city}")
            print(f"    Razão comercial: {razao:.4f}")
            print()
    else:
        print("  Nenhum roteador comercial com endereço encontrado")

    print(f"\n{'='*60}")
    print("  AMOSTRA MANUAL — RESIDENCIAL")
    print(f"{'='*60}")

    # Pegar n roteadores classificados como residencial
    residenciais = df_com_endereco[df_com_endereco["classificacao_kmeans"] == "residencial"]
    if len(residenciais) > 0:
        amostra = residenciais.sample(min(n, len(residenciais)))
        for mac, row in amostra.iterrows():
            loc = row.get("location", "sem endereço")
            city = row.get("city", "sem cidade")
            razao = row.get("razao_comercial", 0)
            print(f"  {mac}")
            print(f"    Endereço: {loc}")
            print(f"    Cidade: {city}")
            print(f"    Razão comercial: {razao:.4f}")
            print()
    else:
        print("  Nenhum roteador residencial com endereço encontrado")


# ============================================================
# FUNÇÃO 3: Distribuição por cidade
# ============================================================
def distribuicao_por_cidade(df):
    """Mostra a distribuição de comercial vs residencial por cidade.

    Se uma cidade é predominantemente residencial, a maioria dos
    roteadores deveria ser classificada como residencial.
    """
    print(f"\n{'='*60}")
    print("  DISTRIBUIÇÃO POR CIDADE")
    print(f"{'='*60}")

    if "city" not in df.columns:
        print("  Coluna 'city' não encontrada")
        return

    # Contar classificação por cidade
    tabela = pd.crosstab(df["city"], df["classificacao_kmeans"], margins=True)
    print(tabela)

    # Calcular % comercial por cidade
    print(f"\n→ Percentual comercial por cidade:")
    for city in df["city"].dropna().unique():
        dados_city = df[df["city"] == city]
        total = len(dados_city)
        comercial = (dados_city["classificacao_kmeans"] == "comercial").sum()
        pct = (comercial / total) * 100 if total > 0 else 0
        print(f"  {city}: {comercial}/{total} ({pct:.1f}%) comercial")


# ============================================================
# FUNÇÃO 4: Estatísticas por cidade
# ============================================================
def estatisticas_por_cidade(df):
    """Mostra a razão comercial média e hora de pico por cidade."""
    print(f"\n{'='*60}")
    print("  ESTATÍSTICAS POR CIDADE")
    print(f"{'='*60}")

    if "city" not in df.columns:
        print("  Coluna 'city' não encontrada")
        return

    # Agrupar por cidade
    stats = df.groupby("city").agg({
        "razao_comercial": "mean",
        "hora_pico": "mean",
    }).round(4)

    # Contar roteadores por cidade
    stats["total_roteadores"] = df.groupby("city").size()

    print(stats)


# ============================================================
# FUNÇÃO 5: Criar mapa (opcional, precisa de folium)
# ============================================================
def criar_mapa(df):
    """Cria um mapa HTML com os roteadores coloridos por classificação.

    Vermelho = comercial
    Azul = residencial
    Cinza = padrão anômalo

    Requer a biblioteca folium: pip install folium
    """
    print(f"\n{'='*60}")
    print("  MAPA DE CLASSIFICAÇÃO")
    print(f"{'='*60}")

    # Verificar se tem coordenadas
    if "latitude" not in df.columns or "longitude" not in df.columns:
        print("  Colunas latitude/longitude não encontradas")
        return

    # Filtrar só roteadores com coordenadas válidas
    com_coords = df.dropna(subset=["latitude", "longitude"])
    print(f"  Roteadores com coordenadas: {len(com_coords)}")

    if len(com_coords) == 0:
        print("  Nenhum roteador com coordenadas válidas")
        return

    try:
        import folium
    except ImportError:
        print("  Biblioteca 'folium' não instalada. Instale com: pip install folium")
        return

    # Centro do mapa (média das coordenadas)
    centro = [com_coords["latitude"].mean(), com_coords["longitude"].mean()]
    mapa = folium.Map(location=centro, zoom_start=10)

    # Cores por classificação
    cores = {
        "comercial": "red",
        "residencial": "blue",
        "padrao_anomalo": "gray"
    }

    # Adicionar marcadores
    for mac, row in com_coords.iterrows():
        classe = row.get("classificacao_kmeans", "residencial")
        cor = cores.get(classe, "green")

        # Texto do popup
        popup_text = f"""
        <b>Router:</b> {mac}<br>
        <b>Classificação:</b> {classe}<br>
        <b>Cidade:</b> {row.get('city', 'N/A')}<br>
        <b>Razão comercial:</b> {row.get('razao_comercial', 0):.4f}
        """

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color=cor,
            fill=True,
            fillColor=cor,
            fillOpacity=0.7,
            popup=folium.Popup(popup_text, max_width=200)
        ).add_to(mapa)

    # Salvar mapa
    os.makedirs("data/processed", exist_ok=True)
    caminho = "data/processed/mapa_classificacao.html"
    mapa.save(caminho)
    print(f"  ✅ Mapa salvo em {caminho}")
    print(f"     Abra no navegador para ver os roteadores no mapa")


# ============================================================
# FUNÇÃO 6: Validar concordância por cidade
# ============================================================
def concordancia_por_cidade(df):
    """Mostra a concordância entre regra e K-Means por cidade."""
    print(f"\n{'='*60}")
    print("  CONCORDÂNCIA POR CIDADE")
    print(f"{'='*60}")

    if "city" not in df.columns:
        print("  Coluna 'city' não encontrada")
        return

    for city in df["city"].dropna().unique():
        dados_city = df[df["city"] == city]
        total = len(dados_city)
        concordam = (dados_city["classificacao_regra"] == dados_city["classificacao_kmeans"]).sum()
        pct = (concordam / total) * 100 if total > 0 else 0
        print(f"  {city}: {concordam}/{total} ({pct:.1f}%)")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    """Executa todas as validações."""
    print("=" * 60)
    print("  AVALIAÇÃO — ETAPA 6")
    print("=" * 60)

    # 1. Juntar classificação com localização
    df = juntar_dados()

    if len(df) == 0:
        print("❌ Nenhum roteador com classificação E localização!")
        return

    # 2. Amostra manual
    amostra_manual(df, n=10)

    # 3. Distribuição por cidade
    distribuicao_por_cidade(df)

    # 4. Estatísticas por cidade
    estatisticas_por_cidade(df)

    # 5. Concordância por cidade
    concordancia_por_cidade(df)

    # 6. Mapa (opcional)
    criar_mapa(df)

    # 7. Salvar resultado com localização
    print(f"\n{'='*60}")
    print("  SALVANDO RESULTADO")
    print(f"{'='*60}")
    caminho = "data/processed/avaliacao_ia_2026-04-01.csv"
    df.to_csv(caminho)
    print(f"✅ Avaliação salva em {caminho}")
    print(f"   {len(df)} roteadores com classificação + localização")

    print(f"\n{'='*60}")
    print("  AVALIAÇÃO CONCLUÍDA!")
    print(f"{'='*60}")


# ============================================================
# Executa se o arquivo for chamado diretamente
# python avaliacao_ia.py
# ============================================================
if __name__ == "__main__":
    main()