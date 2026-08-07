"""
modelo_hdbscan_ia.py — Modelagem com HDBSCAN (Alternativa ao K-Means)
============================================================
ETAPA 5 DO PROJETO: MODELAGEM (ALTERNATIVA)
============================================================

Este arquivo implementa o HDBSCAN como alternativa ao K-Means.

Por que HDBSCAN?
  1. NÃO precisa escolher K (número de grupos) — descobre sozinho
  2. Detecta outliers AUTOMATICAMENTE (marca como -1)
  3. Encontra grupos de qualquer forma (não só circulares)
  4. Só precisa de 1 parâmetro: min_cluster_size

Diferenças do K-Means:
  - K-Means: precisa K, não lida com outliers, grupos circulares
  - HDBSCAN: não precisa K, outliers automáticos, grupos de qualquer forma

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import numpy as np
import os

# Tentar importar HDBSCAN
try:
    from hdbscan import HDBSCAN
    HDBSCAN_DISPONIVEL = True
except ImportError:
    HDBSCAN_DISPONIVEL = False
    print("[hdbscan] Biblioteca 'hdbscan' não instalada.")
    print("[hdbscan] Instale com: pip install hdbscan")
    print("[hdbscan] Usando scikit-learn HDBSCAN como alternativa...")
    from sklearn.cluster import HDBSCAN

# ============================================================
# Carregar as features (resultado da Etapa 4)
# ============================================================
if os.path.exists("data/processed/features_todos_dias.csv"):
    df = pd.read_csv("data/processed/features_todos_dias.csv", index_col="router_mac")
    print(f"[hdbscan] Lendo features_todos_dias.csv ({len(df)} linhas)")
else:
    df = pd.read_csv("data/processed/features_2026-04-01.csv", index_col="router_mac")
    print(f"[hdbscan] Lendo features_2026-04-01.csv ({len(df)} linhas)")


# ============================================================
# AGREGAR: média de todos os dias (2 perfis: úteis vs fds)
# ============================================================
# NOTA: HDBSCAN não usa votação por mês como o K-Means.
# O HDBSCAN pode encontrar números diferentes de clusters em cada mês,
# o que tornaria a votação impossível (não dá para votar entre 2 grupos
# em um mês e 3 grupos em outro).
#
# Em vez disso, agregamos todos os meses juntos (média) e deixamos
# o HDBSCAN encontrar os grupos.
if df.index.duplicated().any():
    print(f"[hdbscan] Detectadas linhas duplicadas (múltiplos dias por roteador)")
    print(f"[hdbscan] Agregando por roteador (2 perfis: úteis vs fds)...")

    colunas_perfil = [f"h_{i}" for i in range(24)]

    if "eh_fds" in df.columns:
        df_uteis = df[df["eh_fds"] == False].copy()
        df_fds = df[df["eh_fds"] == True].copy()

        agg_uteis = df_uteis.groupby(level=0)[colunas_perfil].mean()
        agg_fds = df_fds.groupby(level=0)[colunas_perfil].mean()

        agg_uteis.columns = [f"uteis_{c}" for c in agg_uteis.columns]
        agg_fds.columns = [f"fds_{c}" for c in agg_fds.columns]

        agregado = agg_uteis.join(agg_fds, how="outer").fillna(0)

        if "razao_comercial" in df.columns:
            agregado["razao_comercial"] = df.groupby(level=0)["razao_comercial"].mean()

        colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
        if all(c in agregado.columns for c in colunas_uteis):
            agregado["hora_pico"] = (
                agregado[colunas_uteis].idxmax(axis=1)
                .str.replace("uteis_h_", "")
                .astype(int)
            )

        df = agregado
        print(f"[hdbscan] Após agregação: {len(df)} roteadores únicos")
        print(f"[hdbscan] Features: {len(df.columns)} colunas")


# ============================================================
# FUNÇÃO 1: Regra de negócio (mesma do K-Means)
# ============================================================
def classificar_regra(df):
    """Classifica roteadores usando a regra de negócio (baseline)."""
    classificacao = df["razao_comercial"].apply(
        lambda r: "comercial" if r > 0.5 else "residencial"
    )
    print(f"[regra] Total: {len(classificacao)} roteadores")
    print(f"[regra] Comercial: {(classificacao == 'comercial').sum()}")
    print(f"[regra] Residencial: {(classificacao == 'residencial').sum()}")
    return classificacao


# ============================================================
# FUNÇÃO 2: HDBSCAN (clustering)
# ============================================================
def classificar_hdbscan(df, min_cluster_size=50):
    """Agrupa roteadores usando HDBSCAN.

    Diferenças do K-Means:
    - Não precisa escolher K (número de grupos)
    - Outliers são marcados como -1 automaticamente
    - Encontra grupos de qualquer forma

    Parâmetros:
        df: DataFrame com as colunas do perfil horário
        min_cluster_size: tamanho mínimo para formar um grupo
                         (valor pequeno = mais grupos, valor grande = menos grupos)

    Retorna:
        Series com o grupo de cada roteador (-1 = outlier/ruído)
    """
    # 1. Selecionar as colunas do perfil horário
    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]

    if all(c in df.columns for c in colunas_uteis):
        perfil = df[colunas_uteis + colunas_fds]
        print(f"[hdbscan] Usando 2 perfis (úteis + fds): {len(perfil.columns)} colunas")
    else:
        colunas_simples = [f"h_{i}" for i in range(24)]
        perfil = df[colunas_simples]
        print(f"[hdbscan] Usando 1 perfil: {len(perfil.columns)} colunas")

    # 2. Normalizar com L1 (mesma do K-Means)
    soma_por_router = perfil.sum(axis=1)
    perfil_normalizado = perfil.div(soma_por_router, axis=0)

    # 2.5. Reduzir dimensionalidade com PCA (maldição da dimensionalidade)
    # O HDBSCAN não funciona bem em 48 dimensões (todos os pontos ficam
    # a uma distância similar). O PCA reduz para poucas dimensões mantendo
    # a informação principal.
    #
    # Testamos 2D (29% variância, agrupou por volume) e 10D (65% variância, não agrupou).
    # 3D é o meio-termo: suficiente para manter o padrão, pouco para o HDBSCAN ver densidade.
    from sklearn.decomposition import PCA
    pca = PCA(n_components=3, random_state=42)
    perfil_pca = pca.fit_transform(perfil_normalizado)
    print(f"[hdbscan] PCA: 48 dimensões → {pca.n_components_} dimensões")
    print(f"[hdbscan] Variância explicada: {pca.explained_variance_ratio_.sum():.2%}")

    # 3. Criar e treinar o HDBSCAN
    # min_cluster_size: mínimo de roteadores para formar um grupo
    # min_samples: quão conservador ao decidir se um ponto é núcleo ou ruído
    #   - min_samples baixo (3-5) = mais permissivo, menos ruído
    #   - min_samples alto (10+) = mais conservador, mais ruído
    print(f"[hdbscan] min_cluster_size = {min_cluster_size}, min_samples = 5")
    clusterer = HDBSCAN(min_cluster_size=min_cluster_size, min_samples=5)
    grupos = clusterer.fit_predict(perfil_pca)

    # 4. Converter para Series
    grupos_series = pd.Series(grupos, index=df.index, name="grupo_hdbscan")

    # 5. Contar quantos roteadores em cada grupo
    print(f"[hdbscan] Total: {len(grupos_series)} roteadores")
    grupos_unicos = sorted(grupos_series.unique())
    for g in grupos_unicos:
        qtd = (grupos_series == g).sum()
        if g == -1:
            print(f"[hdbscan] Ruído/Outlier (-1): {qtd} roteadores")
        else:
            print(f"[hdbscan] Grupo {g}: {qtd} roteadores")

    print(f"[hdbscan] Número de grupos encontrados: {len(grupos_unicos) - (1 if -1 in grupos_unicos else 0)}")

    return grupos_series


# ============================================================
# FUNÇÃO 3: Interpretar os grupos do HDBSCAN
# ============================================================
def interpretar_grupos_hdbscan(df, grupos):
    """Descobre qual grupo é comercial e qual é residencial.

    Usa a razao_comercial média (igual ao K-Means).
    Outliers (-1) são classificados como "padrao_anomalo".
    """
    df_com_grupos = df.copy()
    df_com_grupos["grupo_hdbscan"] = grupos

    # Separar outliers (-1) dos grupos normais
    mascara_outlier = grupos == -1
    mascara_normal = ~mascara_outlier

    # Classificar outliers como "padrao_anomalo"
    classificacao_outliers = pd.Series(
        "padrao_anomalo", index=grupos[mascara_outlier].index, name="classificacao_hdbscan"
    )

    # Interpretar grupos normais
    grupos_normais = grupos[mascara_normal]
    df_normais = df_com_grupos[mascara_normal]

    # Se só tem 1 grupo, todos são o mesmo
    grupos_unicos = sorted(grupos_normais.unique())

    if len(grupos_unicos) == 1:
        print(f"[interpretar] HDBSCAN encontrou só 1 grupo + outliers")
        print(f"[interpretar] Todos os roteadores normais são do mesmo tipo")
        # Usar razao_comercial média para decidir
        razao_media = df_normais["razao_comercial"].mean()
        if razao_media > 0.5:
            classe = "comercial"
        else:
            classe = "residencial"
        classificacao_normais = pd.Series(
            classe, index=grupos_normais.index, name="classificacao_hdbscan"
        )
    else:
        # Múltiplos grupos: interpretar pela razao_comercial
        razao_por_grupo = df_normais.groupby("grupo_hdbscan")["razao_comercial"].mean()

        print(f"[interpretar] Razão comercial média por grupo:")
        for g, r in razao_por_grupo.items():
            print(f"[interpretar]   Grupo {g}: razao_comercial média = {r:.4f}")

        # Ordenar grupos por razao_comercial
        grupos_ordenados = razao_por_grupo.sort_values()

        # Se tem 2 grupos: menor = residencial, maior = comercial
        if len(grupos_ordenados) == 2:
            grupo_residencial = grupos_ordenados.index[0]
            grupo_comercial = grupos_ordenados.index[1]
            mapeamento = {
                grupo_comercial: "comercial",
                grupo_residencial: "residencial"
            }
        else:
            # Se tem mais de 2 grupos: classificar por razao_comercial
            # > 0.5 = comercial, <= 0.5 = residencial
            print(f"[interpretar] HDBSCAN encontrou {len(grupos_ordenados)} grupos!")
            print(f"[interpretar] Classificando por razao_comercial (> 0.5 = comercial)")
            mapeamento = {}
            for g in grupos_ordenados.index:
                razao = razao_por_grupo[g]
                if razao > 0.5:
                    mapeamento[g] = "comercial"
                else:
                    mapeamento[g] = "residencial"

        classificacao_normais = grupos_normais.map(mapeamento)

    # Juntar normais + outliers
    classificacao_final = pd.concat([classificacao_normais, classificacao_outliers])

    # Garantir que o índice está na mesma ordem do df original
    classificacao_final = classificacao_final.reindex(df.index)

    return classificacao_final


# ============================================================
# FUNÇÃO 4: Comparar regra vs HDBSCAN
# ============================================================
def comparar_metodos(regra, hdbscan):
    """Compara as duas abordagens e calcula a concordância."""
    comparacao = pd.DataFrame({
        "regra": regra,
        "hdbscan": hdbscan
    })

    concordam = (comparacao["regra"] == comparacao["hdbscan"]).sum()
    discordam = (comparacao["regra"] != comparacao["hdbscan"]).sum()
    total = len(comparacao)
    pct_concordancia = (concordam / total) * 100

    print(f"[comparar] Total: {total} roteadores")
    print(f"[comparar] Concordam: {concordam} ({pct_concordancia:.1f}%)")
    print(f"[comparar] Discordam: {discordam} ({100 - pct_concordancia:.1f}%)")

    print(f"\n[comparar] Matriz de confusão:")
    matriz = pd.crosstab(comparacao["regra"], comparacao["hdbscan"], margins=True)
    print(matriz)

    return comparacao


# ============================================================
# FUNÇÃO 5: Analisar perfil horário de cada grupo
# ============================================================
def analisar_perfil_grupos(df, grupos):
    """Mostra o perfil horário médio de cada grupo."""
    df_com_grupos = df.copy()
    df_com_grupos["grupo"] = grupos

    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]

    tem_2_perfis = all(c in df.columns for c in colunas_uteis)

    if tem_2_perfis:
        for tipo, colunas in [("DIAS ÚTEIS", colunas_uteis), ("FINS DE SEMANA", colunas_fds)]:
            print(f"\n[perfil] === {tipo} ===")
            perfil_medio = df_com_grupos.groupby("grupo")[colunas].mean()
            for g in perfil_medio.index:
                if g == -1:
                    print(f"\n[perfil] Ruído/Outlier (-1):")
                else:
                    print(f"\n[perfil] Grupo {g}:")
                top5 = perfil_medio.loc[g].nlargest(5)
                for hora, valor in top5.items():
                    print(f"[perfil]   {hora}: {valor:,.0f} bytes")
    else:
        colunas_simples = [f"h_{i}" for i in range(24)]
        perfil_medio = df_com_grupos.groupby("grupo")[colunas_simples].mean()
        print(f"[perfil] Perfil horário médio por grupo:")
        for g in perfil_medio.index:
            print(f"\n[perfil] Grupo {g}:")
            top5 = perfil_medio.loc[g].nlargest(5)
            for hora, valor in top5.items():
                print(f"[perfil]   {hora}: {valor:,.0f} bytes")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    """Executa o HDBSCAN e compara com a regra."""
    global df

    print("=" * 60)
    print("  MODELAGEM COM HDBSCAN — ALTERNATIVA AO K-MEANS")
    print("=" * 60)

    print(f"\n→ Dados carregados: {len(df)} roteadores × {len(df.columns)} features")

    # 1. Regra de negócio
    print("\n" + "=" * 60)
    print("  ABORDAGEM 1: REGRA DE NEGÓCIO (baseline)")
    print("=" * 60)
    classificacao_regra = classificar_regra(df)

    # 2. HDBSCAN
    print("\n" + "=" * 60)
    print("  ABORDAGEM 2: HDBSCAN (clustering)")
    print("=" * 60)
    grupos_hdbscan = classificar_hdbscan(df, min_cluster_size=50)

    # 3. Interpretar grupos
    print("\n" + "=" * 60)
    print("  INTERPRETAÇÃO DOS GRUPOS")
    print("=" * 60)
    classificacao_hdbscan = interpretar_grupos_hdbscan(df, grupos_hdbscan)

    # 4. Comparar métodos
    print("\n" + "=" * 60)
    print("  COMPARAÇÃO: REGRA vs HDBSCAN")
    print("=" * 60)
    comparacao = comparar_metodos(classificacao_regra, classificacao_hdbscan)

    # 5. Analisar perfil horário
    print("\n" + "=" * 60)
    print("  PERFIL HORÁRIO POR GRUPO")
    print("=" * 60)
    analisar_perfil_grupos(df, grupos_hdbscan)

    # 6. Salvar resultado
    print("\n" + "=" * 60)
    print("  SALVANDO RESULTADOS")
    print("=" * 60)

    resultado = df.copy()
    resultado["classificacao_regra"] = classificacao_regra
    resultado["classificacao_hdbscan"] = classificacao_hdbscan
    resultado["concorda"] = resultado["classificacao_regra"] == resultado["classificacao_hdbscan"]

    os.makedirs("data/processed", exist_ok=True)
    resultado.to_csv("data/processed/classificacao_hdbscan_2026-04-01.csv")
    print(f"✅ Resultado salvo em data/processed/classificacao_hdbscan_2026-04-01.csv")
    print(f"   {len(resultado)} roteadores classificados")

    # Resumo final
    print("\n" + "=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)
    print(f"  Regra de negócio:")
    print(f"    Comercial:      {(classificacao_regra == 'comercial').sum()}")
    print(f"    Residencial:    {(classificacao_regra == 'residencial').sum()}")
    print(f"  HDBSCAN:")
    print(f"    Comercial:      {(classificacao_hdbscan == 'comercial').sum()}")
    print(f"    Residencial:    {(classificacao_hdbscan == 'residencial').sum()}")
    print(f"    Padrão anômalo: {(classificacao_hdbscan == 'padrao_anomalo').sum()}")
    concordancia = (classificacao_regra == classificacao_hdbscan).mean() * 100
    print(f"  Concordância:  {concordancia:.1f}%")
    print("=" * 60)
    print("  MODELAGEM HDBSCAN CONCLUÍDA!")
    print("=" * 60)

    return resultado


# ============================================================
# Executa se o arquivo for chamado diretamente
# python modelo_hdbscan_ia.py
# ============================================================
if __name__ == "__main__":
    main()