"""
classificacao_endereco_ia.py — Classificação por Endereço (Ground Truth Automático)
============================================================
ETAPA 6 DO PROJETO: VALIDAÇÃO AUTOMÁTICA POR ENDEREÇO
============================================================

Classifica roteadores como residencial ou comercial baseado
em palavras-chave no endereço (coluna `location` da tabela routers).

METODOLOGIA:
  1. Carrega a tabela routers (com endereços)
  2. Deduplica pegando a versão mais recente de cada roteador
  3. Para cada endereço, procura palavras-chave:
     - "casa", "ap", "apto", "condomínio", "lote", "lot" → RESIDENCIAL
     - "loja", "sala", "imobiliária", "comércio", "empresa" → COMERCIAL
  4. Compara com a classificação do modelo (regra + K-Means)

COMO USAR:
  python classificacao_endereco_ia.py

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import re

# ============================================================
# PALAVRAS-CHAVE PARA CLASSIFICAÇÃO POR ENDEREÇO
# ============================================================
# Lista de palavras que indicam uso RESIDENCIAL
# (minúsculas — o código converte o endereço para minúsculo antes de buscar)
PALAVRAS_RESIDENCIAL = [
    "casa",
    "ap.",
    "apto",
    "apartamento",
    "condomínio",
    "condominio",
    "lote",
    "lot ",
    "residência",
    "residencia",
    "vila",
    "chácara",
    "chacara",
    "sítio",
    "sitio",
    "fazenda",
    "km ",          # zona rural (ex: "KM 22")
    "quadra",       # condomínio residencial
    "bloco",        # condomínio residencial
]

# Lista de palavras que indicam uso COMERCIAL
PALAVRAS_COMERCIAL = [
    "loja",
    "sala",
    "sla",          # abreviação comum de "sala"
    "imobiliária",
    "imobiliaria",
    "comércio",
    "comercio",
    "empresa",
    "escritório",
    "escritorio",
    "shopping",
    "galeria",
    "centro comercial",
    "ponto comercial",
    "box ",         # box em galeria comercial
    "galpão",
    "galpao",
    "deposito",
    "depósito",
]


# ============================================================
# FUNÇÃO 1: Classificar um endereço
# ============================================================
def classificar_endereco(endereco):
    """Classifica um endereço como residencial, comercial ou indefinido.

    Procura palavras-chave no endereço. Se encontrar palavra residencial,
    classifica como residencial. Se encontrar palavra comercial, classifica
    como comercial. Se encontrar AMBAS ou NENHUMA, classifica como indefinido.

    Parâmetros:
        endereco: string com o endereço do roteador

    Retorna:
        "residencial", "comercial" ou "indefinido"
    """
    if pd.isna(endereco) or not isinstance(endereco, str):
        return "indefinido"

    # Converter para minúsculo para comparar sem diferenciar maiúsculas
    end_lower = endereco.lower()

    # Procurar palavras-chave
    achou_residencial = any(palavra in end_lower for palavra in PALAVRAS_RESIDENCIAL)
    achou_comercial = any(palavra in end_lower for palavra in PALAVRAS_COMERCIAL)

    # Decisão
    if achou_residencial and not achou_comercial:
        return "residencial"
    elif achou_comercial and not achou_residencial:
        return "comercial"
    elif achou_residencial and achou_comercial:
        # Ambas as palavras encontradas — não dá para decidir com certeza
        return "indefinido"
    else:
        # Nenhuma palavra encontrada — endereço não tem indicador claro
        return "indefinido"


# ============================================================
# FUNÇÃO 2: Carregar e preparar os dados
# ============================================================
def carregar_dados():
    """Carrega a tabela routers e a classificação do modelo.

    Retorna:
        df: DataFrame com roteadores que têm endereço E classificação do modelo
    """
    # Carregar routers (tabela de localização)
    routers = pd.read_csv("data/raw/routers.csv", parse_dates=["timestamp"])

    # Deduplicar pegando a versão mais recente de cada roteador
    routers = routers.sort_values("timestamp", ascending=False).drop_duplicates(
        "router_mac", keep="first"
    )
    routers = routers.set_index("router_mac")

    # Filtrar só roteadores que TÊM endereço (location não nulo)
    routers_com_endereco = routers.dropna(subset=["location"])
    print(f"[endereco] Roteadores com endereço: {len(routers_com_endereco)}")

    # Carregar classificação do modelo
    try:
        classificacao = pd.read_csv(
            "data/processed/classificacao_ia_2026-04-01.csv",
            index_col="router_mac"
        )
    except FileNotFoundError:
        print("❌ Arquivo de classificação não encontrado!")
        print("   Rode o modelo_ia.py primeiro.")
        return None

    print(f"[endereco] Classificação do modelo: {len(classificacao)} roteadores")

    # Juntar (inner join: só roteadores que têm endereço E classificação)
    df = classificacao.join(
        routers_com_endereco[["location", "city", "state", "latitude", "longitude"]],
        how="inner"
    )
    print(f"[endereco] Roteadores com endereço E classificação: {len(df)}")

    return df


# ============================================================
# FUNÇÃO 3: Classificar todos os endereços
# ============================================================
def classificar_todos(df):
    """Aplica a classificação por endereço em todos os roteadores.

    Parâmetros:
        df: DataFrame com a coluna 'location'

    Retorna:
        Series com a classificação por endereço
    """
    classificacao_end = df["location"].apply(classificar_endereco)

    # Contar resultados
    print(f"\n[endereco] Classificação por endereço:")
    print(f"  Residencial: {(classificacao_end == 'residencial').sum()}")
    print(f"  Comercial:   {(classificacao_end == 'comercial').sum()}")
    print(f"  Indefinido:  {(classificacao_end == 'indefinido').sum()}")

    return classificacao_end


# ============================================================
# FUNÇÃO 4: Comparar classificação por endereço vs modelo
# ============================================================
def comparar(df, classificacao_end):
    """Compara a classificação por endereço com a do modelo.

    Só compara roteadores onde o endereço deu uma classificação
    definida (residencial ou comercial), ignorando os indefinidos.

    Parâmetros:
        df: DataFrame com a classificação do modelo
        classificacao_end: Series com a classificação por endereço
    """
    # Filtrar só roteadores com classificação definida pelo endereço
    mascara_definida = classificacao_end.isin(["residencial", "comercial"])
    df_comparar = df[mascara_definida].copy()
    end_definido = classificacao_end[mascara_definida]

    print(f"\n{'='*60}")
    print("  COMPARAÇÃO: ENDEREÇO vs MODELO")
    print(f"{'='*60}")
    print(f"  Roteadores comparáveis (endereço definido): {len(df_comparar)}")

    if len(df_comparar) == 0:
        print("  Nenhum roteador com endereço classificável.")
        return

    # Comparar com regra
    acertos_regra = (df_comparar["classificacao_regra"] == end_definido).sum()
    pct_regra = acertos_regra / len(df_comparar) * 100

    # Comparar com K-Means
    acertos_kmeans = (df_comparar["classificacao_kmeans"] == end_definido).sum()
    pct_kmeans = acertos_kmeans / len(df_comparar) * 100

    print(f"\n  Acertos da REGRA:     {acertos_regra}/{len(df_comparar)} ({pct_regra:.1f}%)")
    print(f"  Acertos do K-MEANS:   {acertos_kmeans}/{len(df_comparar)} ({pct_kmeans:.1f}%)")

    # Matriz de confusão — Regra
    print(f"\n  Matriz de confusão (Regra vs Endereço):")
    matriz_regra = pd.crosstab(
        end_definido,
        df_comparar["classificacao_regra"],
        rownames=["Endereço"],
        colnames=["Regra"],
        margins=True
    )
    print(matriz_regra)

    # Matriz de confusão — K-Means
    print(f"\n  Matriz de confusão (K-Means vs Endereço):")
    matriz_kmeans = pd.crosstab(
        end_definido,
        df_comparar["classificacao_kmeans"],
        rownames=["Endereço"],
        colnames=["K-Means"],
        margins=True
    )
    print(matriz_kmeans)

    # ============================================================
    # CRUZAMENTO COMPLETO: Endereço × K-Means (todas as combinações)
    # ============================================================
    print(f"\n{'='*60}")
    print("  CRUZAMENTO COMPLETO: ENDEREÇO × K-MEANS")
    print(f"{'='*60}")

    # Tabela com todas as combinações possíveis
    cruzamento = pd.crosstab(
        end_definido,
        df_comparar["classificacao_kmeans"],
        rownames=["Endereço (ground truth)"],
        colnames=["K-Means (modelo)"],
        margins=True,
        normalize=False
    )
    print(cruzamento)

    # Versão em percentual (por linha: dentro de cada classe do endereço)
    print(f"\n  Cruzamento em % (por linha — dentro de cada classe do endereço):")
    cruzamento_pct = pd.crosstab(
        end_definido,
        df_comparar["classificacao_kmeans"],
        rownames=["Endereço"],
        colnames=["K-Means"],
        normalize="index"
    ) * 100
    print(cruzamento_pct.round(1))

    # Análise das 4 categorias de cruzamento
    print(f"\n  Análise das combinações:")
    combinacoes = [
        ("residencial", "residencial", "✅ Verdadeiro Residencial"),
        ("residencial", "comercial",   "⚠️  Home Office (residência com padrão comercial)"),
        ("comercial",   "comercial",   "✅ Verdadeiro Comercial"),
        ("comercial",   "residencial", "⚠️  Comércio com padrão residencial"),
    ]
    for end_cls, kmeans_cls, descricao in combinacoes:
        qtd = ((end_definido == end_cls) &
               (df_comparar["classificacao_kmeans"] == kmeans_cls)).sum()
        pct = qtd / len(df_comparar) * 100
        print(f"    {descricao}: {qtd} ({pct:.1f}%)")

    # Concordância entre regra e K-Means dentro de cada grupo do endereço
    print(f"\n  Concordância Regra vs K-Means (dentro de cada grupo do endereço):")
    for end_cls in ["residencial", "comercial"]:
        mascara = end_definido == end_cls
        if mascara.sum() > 0:
            concordam = (
                df_comparar.loc[mascara, "classificacao_regra"] ==
                df_comparar.loc[mascara, "classificacao_kmeans"]
            ).sum()
            total_grupo = mascara.sum()
            print(f"    Endereço={end_cls}: {concordam}/{total_grupo} "
                  f"({concordam/total_grupo*100:.1f}%) concordam")

    # Mostrar erros do K-Means com detalhes
    erros = df_comparar[
        (df_comparar["classificacao_kmeans"] != end_definido)
    ].copy()
    erros["classificacao_endereco"] = end_definido[erros.index]

    if len(erros) > 0:
        print(f"\n  → Erros do K-Means ({len(erros)} roteadores):")
        print(f"  {'Router MAC':<20} {'Endereço':<14} {'Regra':<14} "
              f"{'K-Means':<14} {'Razão':<8} {'Location'}")
        for mac, row in erros.head(30).iterrows():
            loc = str(row.get("location", ""))[:50]
            razao = row.get("razao_comercial", 0)
            print(f"  {mac:<20} {row['classificacao_endereco']:<14} "
                  f"{row['classificacao_regra']:<14} "
                  f"{row['classificacao_kmeans']:<14} {razao:<8.4f} {loc}")
        if len(erros) > 30:
            print(f"  ... e mais {len(erros) - 30} erros")


# ============================================================
# FUNÇÃO 5: Mostrar exemplos de cada classificação
# ============================================================
def mostrar_exemplos(df, classificacao_end, n=10):
    """Mostra exemplos de endereços classificados para inspeção visual.

    Útil para verificar se as palavras-chave estão funcionando.
    """
    df_exemplos = df.copy()
    df_exemplos["classificacao_endereco"] = classificacao_end

    for classe in ["residencial", "comercial", "indefinido"]:
        amostra = df_exemplos[df_exemplos["classificacao_endereco"] == classe]
        print(f"\n{'='*60}")
        print(f"  EXEMPLOS — {classe.upper()} ({len(amostra)} roteadores)")
        print(f"{'='*60}")

        if len(amostra) == 0:
            print("  Nenhum roteador nesta categoria.")
            continue

        for mac, row in amostra.head(n).iterrows():
            loc = row.get("location", "sem endereço")
            city = row.get("city", "sem cidade")
            kmeans = row.get("classificacao_kmeans", "?")
            regra = row.get("classificacao_regra", "?")
            razao = row.get("razao_comercial", 0)
            acertou = "✅" if kmeans == classe else "❌"
            print(f"  {mac}")
            print(f"    Endereço: {loc}")
            print(f"    Cidade: {city}")
            print(f"    Modelo — Regra: {regra} | K-Means: {kmeans} {acertou} | Razão: {razao:.4f}")
            print()


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================
def main():
    """Executa a classificação por endereço e compara com o modelo."""
    print("=" * 60)
    print("  CLASSIFICAÇÃO POR ENDEREÇO — GROUND TRUTH AUTOMÁTICO")
    print("=" * 60)

    # 1. Carregar dados
    print("\n→ Carregando dados...")
    df = carregar_dados()
    if df is None:
        return

    # 2. Classificar por endereço
    print("\n→ Classificando endereços...")
    classificacao_end = classificar_todos(df)

    # 3. Mostrar exemplos
    mostrar_exemplos(df, classificacao_end, n=10)

    # 4. Comparar com modelo
    comparar(df, classificacao_end)

    # 5. Salvar resultado
    print(f"\n{'='*60}")
    print("  SALVANDO RESULTADOS")
    print(f"{'='*60}")

    resultado = df.copy()
    resultado["classificacao_endereco"] = classificacao_end
    resultado.to_csv("data/processed/classificacao_endereco_ia.csv")
    print(f"✅ Resultado salvo em data/processed/classificacao_endereco_ia.csv")
    print(f"   {len(resultado)} roteadores classificados")

    # Resumo final
    print(f"\n{'='*60}")
    print("  RESUMO FINAL")
    print(f"{'='*60}")
    print(f"  Total com endereço: {len(df)}")
    print(f"  Endereço residencial: {(classificacao_end == 'residencial').sum()}")
    print(f"  Endereço comercial:   {(classificacao_end == 'comercial').sum()}")
    print(f"  Endereço indefinido:  {(classificacao_end == 'indefinido').sum()}")
    print(f"{'='*60}")
    print("  CLASSIFICAÇÃO POR ENDEREÇO CONCLUÍDA!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()