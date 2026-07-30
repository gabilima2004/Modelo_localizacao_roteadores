"""
modelo_ia.py — Modelagem (Etapa 5)
============================================================
ETAPA 5 DO PROJETO: MODELAGEM
============================================================

Este arquivo aplica duas abordagens para classificar os roteadores:

  1. REGRA DE NEGÓCIO (baseline, NÃO é ML)
     - Se razao_comercial > 0.5 → comercial
     - Se razao_comercial <= 0.5 → residencial

  2. K-MEANS (clustering, É ML — não supervisionado)
     - Agrupa roteadores por similaridade do perfil horário
     - O algoritmo encontra os grupos sozinho
     - Depois interpretamos: qual grupo é comercial, qual é residencial

  3. COMPARAÇÃO
     - Se os dois métodos concordam → ganhamos confiança
     - Se discordam → investigamos os casos especiais

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import os

# ============================================================
# Carregar as features (resultado da Etapa 4)
# ============================================================
df = pd.read_csv("data/processed/features_2026-04-01.csv", index_col="router_mac")

# ============================================================
# FUNÇÃO 1: Regra de negócio (baseline)
# ============================================================
def classificar_regra(df):
    """Classifica roteadores usando uma regra de negócio simples.

    Regra: se a maioria do tráfego (>50%) ocorre no horário comercial
    (8h-17h), o roteador é classificado como "comercial".
    Caso contrário, é "residencial".

    Esta NÃO é Machine Learning — é programação tradicional.
    Você (humano) definiu a regra. O computador só executa.

    Parâmetros:
        df: DataFrame com a coluna 'razao_comercial'

    Retorna:
        Series com a classificação ("comercial" ou "residencial")
        para cada roteador.
    """
    # Aplicar a regra: razao > 0.5 → comercial, senão → residencial
    classificacao = df["razao_comercial"].apply(
        lambda r: "comercial" if r > 0.5 else "residencial"
    )

    # Contar quantos de cada classe
    print(f"[regra] Total: {len(classificacao)} roteadores")
    print(f"[regra] Comercial: {(classificacao == 'comercial').sum()}")
    print(f"[regra] Residencial: {(classificacao == 'residencial').sum()}")

    return classificacao


# ============================================================
# FUNÇÃO 2: K-Means (clustering — ML não supervisionado)
# ============================================================
def classificar_kmeans(df, k=2):
    """Agrupa roteadores usando K-Means baseado no perfil horário.

    O K-Means encontra grupos de roteadores com perfis horários parecidos.
    Ele NÃO sabe qual é comercial ou residencial — só agrupa os parecidos.
    Depois nós interpretamos os grupos.

    IMPORTANTE: antes do K-Means, é preciso NORMALIZAR os dados.
    Por que? Queremos comparar o PADRÃO (quando o tráfego acontece),
    não o VOLUME (quanto tráfego). Usamos normalização L1: dividir
    cada perfil pela sua soma total. Assim, cada roteador vira uma
    distribuição que soma 1, e comparamos a "forma" do tráfego.

    Parâmetros:
        df: DataFrame com as colunas h_0 a h_23
        k: número de grupos (padrão: 2 — comercial vs residencial)

    Retorna:
        Series com o grupo (0 ou 1) de cada roteador
    """
    # 1. Selecionar só as colunas do perfil horário (h_0 a h_23)
    colunas_perfil = [f"h_{i}" for i in range(24)]
    perfil = df[colunas_perfil]

    # 2. Normalizar por LINHA (cada roteador) — não por coluna!
    # Por que? Queremos comparar o PADRÃO (quando o tráfego acontece),
    # não o VOLUME (quanto tráfego). Sem isso, o K-Means agrupa
    # "roteadores com muito tráfego" vs "pouco tráfego" em vez de
    # "comercial" vs "residencial".
    #
    # Normalização L1: dividir cada perfil pela sua soma total.
    # Assim, cada roteador vira uma distribuição que soma 1.
    # Comparamos a "forma" do tráfego, não o tamanho.
    soma_por_router = perfil.sum(axis=1)
    perfil_normalizado = perfil.div(soma_por_router, axis=0)

    # 3. Criar e treinar o K-Means
    # random_state=42 garante que o resultado seja reproduzível
    # (sem isso, cada execução pode dar um resultado diferente)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    grupos = kmeans.fit_predict(perfil_normalizado)

    # 4. Converter para Series com o mesmo índice do DataFrame
    grupos_series = pd.Series(grupos, index=df.index, name="grupo_kmeans")

    # 5. Contar quantos roteadores em cada grupo
    print(f"[kmeans] Total: {len(grupos_series)} roteadores")
    for g in range(k):
        print(f"[kmeans] Grupo {g}: {(grupos_series == g).sum()} roteadores")

    # 6. Calcular Silhouette Score (métrica de qualidade do clustering)
    # Varia de -1 a 1. Quanto mais perto de 1, melhor separados os grupos.
    silhouette = silhouette_score(perfil_normalizado, grupos)
    print(f"[kmeans] Silhouette Score: {silhouette:.4f}")
    print(f"[kmeans]   (quanto mais perto de 1, melhor)")

    return grupos_series


# ============================================================
# FUNÇÃO 3: Interpretar os grupos do K-Means
# ============================================================
def interpretar_grupos(df, grupos):
    """Descobre qual grupo do K-Means é comercial e qual é residencial.

    O K-Means retorna grupos 0 e 1, mas não diz qual é qual.
    Para descobrir, comparamos a razao_comercial média de cada grupo:
    - O grupo com maior razao_comercial média → comercial
    - O grupo com menor razao_comercial média → residencial
    """
    # Copiar o DataFrame e adicionar a coluna de grupo
    df_com_grupos = df.copy()
    df_com_grupos["grupo_kmeans"] = grupos

    # Calcular a razao_comercial média de cada grupo
    razao_por_grupo = df_com_grupos.groupby("grupo_kmeans")["razao_comercial"].mean()

    print(f"[interpretar] Razão comercial média por grupo:")
    for g, r in razao_por_grupo.items():
        print(f"[interpretar]   Grupo {g}: razao_comercial média = {r:.4f}")

    # O grupo com maior razao_comercial é o comercial
    grupo_comercial = razao_por_grupo.idxmax()
    grupo_residencial = razao_por_grupo.idxmin()

    print(f"[interpretar] Grupo comercial: {grupo_comercial}")
    print(f"[interpretar] Grupo residencial: {grupo_residencial}")

    # Mapear grupos para nomes
    mapeamento = {
        grupo_comercial: "comercial",
        grupo_residencial: "residencial"
    }
    classificacao_kmeans = grupos.map(mapeamento)

    return classificacao_kmeans


# ============================================================
# FUNÇÃO 4: Comparar regra vs K-Means
# ============================================================
def comparar_metodos(regra, kmeans):
    """Compara as duas abordagens e calcula a concordância.

    Se os dois métodos classificam um roteador da mesma forma,
    ganhamos confiança no resultado. Se discordam, investigamos.
    """
    # Criar DataFrame com as duas classificações
    comparacao = pd.DataFrame({
        "regra": regra,
        "kmeans": kmeans
    })

    # Calcular concordância
    concordam = (comparacao["regra"] == comparacao["kmeans"]).sum()
    discordam = (comparacao["regra"] != comparacao["kmeans"]).sum()
    total = len(comparacao)
    pct_concordancia = (concordam / total) * 100

    print(f"[comparar] Total: {total} roteadores")
    print(f"[comparar] Concordam: {concordam} ({pct_concordancia:.1f}%)")
    print(f"[comparar] Discordam: {discordam} ({100 - pct_concordancia:.1f}%)")

    # Mostrar a matriz de confusão
    print(f"\n[comparar] Matriz de confusão:")
    matriz = pd.crosstab(comparacao["regra"], comparacao["kmeans"], margins=True)
    print(matriz)

    return comparacao


# ============================================================
# FUNÇÃO 5: Analisar perfil horário de cada grupo
# ============================================================
def analisar_perfil_grupos(df, grupos):
    """Mostra o perfil horário médio de cada grupo do K-Means.

    Isso ajuda a entender o comportamento de cada grupo:
    - Grupo comercial: pico das 8h-17h
    - Grupo residencial: pico das 18h-23h
    """
    colunas_perfil = [f"h_{i}" for i in range(24)]
    df_com_grupos = df.copy()
    df_com_grupos["grupo"] = grupos

    # Calcular a média do tráfego por hora para cada grupo
    perfil_medio = df_com_grupos.groupby("grupo")[colunas_perfil].mean()

    print(f"[perfil] Perfil horário médio por grupo:")
    for g in perfil_medio.index:
        print(f"\n[perfil] Grupo {g}:")
        # Mostrar as 5 horas com maior tráfego médio
        top5 = perfil_medio.loc[g].nlargest(5)
        for hora, valor in top5.items():
            print(f"[perfil]   {hora}: {valor:,.0f} bytes")

    return perfil_medio


# ============================================================
# FUNÇÃO PRINCIPAL: Orquestra toda a modelagem
# ============================================================
def main():
    """Executa as duas abordagens e compara os resultados."""
    global df  # permite modificar a variável df definida fora da função

    print("=" * 60)
    print("  MODELAGEM — ETAPA 5")
    print("=" * 60)

    # Mostrar informações dos dados carregados
    print(f"\n→ Dados carregados: {len(df)} roteadores × {len(df.columns)} features")

    # 0. Remover outliers (roteadores com tráfego absurdamente alto)
    # O K-Means é sensível a outliers — um roteador com tráfego 449x a mediana
    # atrai um centroide só para ele e arruína o clustering.
    print("\n→ Passo 0: Removendo outliers...")
    colunas_perfil = [f"h_{i}" for i in range(24)]
    trafego_total = df[colunas_perfil].sum(axis=1)
    mediana = trafego_total.median()
    mascara_sem_outlier = trafego_total < (mediana * 100)
    outliers = ~mascara_sem_outlier
    print(f"   Mediana do tráfego total: {mediana:,.0f}")
    print(f"   Outliers removidos: {outliers.sum()}")
    print(f"   Roteadores restantes: {mascara_sem_outlier.sum()}")
    df = df[mascara_sem_outlier]

    # 1. Regra de negócio
    print("\n" + "=" * 60)
    print("  ABORDAGEM 1: REGRA DE NEGÓCIO (baseline)")
    print("=" * 60)
    classificacao_regra = classificar_regra(df)

    # 2. K-Means
    print("\n" + "=" * 60)
    print("  ABORDAGEM 2: K-MEANS (clustering)")
    print("=" * 60)
    grupos_kmeans = classificar_kmeans(df, k=2)

    # 3. Interpretar grupos
    print("\n" + "=" * 60)
    print("  INTERPRETAÇÃO DOS GRUPOS")
    print("=" * 60)
    classificacao_kmeans = interpretar_grupos(df, grupos_kmeans)

    # 4. Comparar métodos
    print("\n" + "=" * 60)
    print("  COMPARAÇÃO: REGRA vs K-MEANS")
    print("=" * 60)
    comparacao = comparar_metodos(classificacao_regra, classificacao_kmeans)

    # 5. Analisar perfil horário
    print("\n" + "=" * 60)
    print("  PERFIL HORÁRIO POR GRUPO")
    print("=" * 60)
    analisar_perfil_grupos(df, grupos_kmeans)

    # 6. Salvar resultado final
    print("\n" + "=" * 60)
    print("  SALVANDO RESULTADOS")
    print("=" * 60)

    # Criar tabela final com as classificações
    resultado = df.copy()
    resultado["classificacao_regra"] = classificacao_regra
    resultado["classificacao_kmeans"] = classificacao_kmeans
    resultado["concorda"] = resultado["classificacao_regra"] == resultado["classificacao_kmeans"]

    # Salvar
    os.makedirs("data/processed", exist_ok=True)
    resultado.to_csv("data/processed/classificacao_ia_2026-04-01.csv")
    print(f"✅ Resultado salvo em data/processed/classificacao_ia_2026-04-01.csv")
    print(f"   {len(resultado)} roteadores classificados")

    # Resumo final
    print("\n" + "=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)
    print(f"  Regra de negócio:")
    print(f"    Comercial:    {(classificacao_regra == 'comercial').sum()}")
    print(f"    Residencial:  {(classificacao_regra == 'residencial').sum()}")
    print(f"  K-Means:")
    print(f"    Comercial:    {(classificacao_kmeans == 'comercial').sum()}")
    print(f"    Residencial:  {(classificacao_kmeans == 'residencial').sum()}")
    concordancia = (classificacao_regra == classificacao_kmeans).mean() * 100
    print(f"  Concordância:  {concordancia:.1f}%")
    print("=" * 60)
    print("  MODELAGEM CONCLUÍDA!")
    print("=" * 60)

    return resultado


# ============================================================
# Executa se o arquivo for chamado diretamente
# python modelo_ia.py
# ============================================================
if __name__ == "__main__":
    main()