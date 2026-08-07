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
# Tenta ler o arquivo consolidado (todos os dias).
# Se não existir, lê o de um dia só (compatibilidade).
import os

if os.path.exists("data/processed/features_todos_dias.csv"):
    df = pd.read_csv("data/processed/features_todos_dias.csv", index_col="router_mac")
    print(f"[modelo] Lendo features_todos_dias.csv ({len(df)} linhas)")
else:
    df = pd.read_csv("data/processed/features_2026-04-01.csv", index_col="router_mac")
    print(f"[modelo] Lendo features_2026-04-01.csv ({len(df)} linhas)")

# ============================================================
# AGREGAR: votação por mês (lida com sazonalidade)
# ============================================================
# O features_todos_dias.csv tem uma linha por roteador POR DIA.
# Descobrimos que 4918 roteadores têm alta variabilidade entre meses
# (std > 0.1). Fazer a média de todos os meses dilui padrões sazonais
# (ex: férias em julho, Copa do Mundo).
#
# Solução: Votação por mês.
# 1. Para cada mês, agregamos os dias úteis e fds (2 perfis).
# 2. O K-Means classifica o roteador em cada mês separadamente.
# 3. A classificação final é a que teve mais votos (a moda).
#
# Isso faz com que um mês atípico (férias) não consiga mudar a
# classificação final sozinho.
if df.index.duplicated().any():
    print(f"[modelo] Detectadas linhas duplicadas (múltiplos dias por roteador)")
    print(f"[modelo] Agregando por mês e aplicando votação...")

    colunas_perfil = [f"h_{i}" for i in range(24)]

    if "mes" not in df.columns:
        print(f"[modelo] Coluna 'mes' não encontrada — usando agregação simples (média de todos os dias)")
        # (código antigo de compatibilidade mantido)
        if "eh_fds" in df.columns:
            df_uteis = df[df["eh_fds"] == False].copy()
            df_fds = df[df["eh_fds"] == True].copy()
            agg_uteis = df_uteis.groupby(df_uteis.index)[colunas_perfil].mean()
            agg_fds = df_fds.groupby(df_fds.index)[colunas_perfil].mean()
            agg_uteis.columns = [f"uteis_{c}" for c in agg_uteis.columns]
            agg_fds.columns = [f"fds_{c}" for c in agg_fds.columns]
            agregado = agg_uteis.join(agg_fds, how="outer").fillna(0)
            if "razao_comercial" in df.columns:
                agregado["razao_comercial"] = df.groupby(df.index)["razao_comercial"].mean()
            colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
            if all(c in agregado.columns for c in colunas_uteis):
                agregado["hora_pico"] = agregado[colunas_uteis].idxmax(axis=1).str.replace("uteis_h_", "").astype(int)
            df = agregado
        else:
            colunas_media = [f"h_{i}" for i in range(24)] + ["razao_comercial"]
            df = df.groupby(df.index)[[c for c in colunas_media if c in df.columns]].mean()
        print(f"[modelo] Após agregação: {len(df)} roteadores únicos")

    else:
        # --- NOVA LÓGICA: VOTAÇÃO POR MÊS ---
        meses = sorted(df["mes"].unique())
        print(f"[modelo] Meses encontrados: {meses}")

        # Guardar a classificação de cada roteador em cada mês
        votos_por_router = {}

        for mes in meses:
            df_mes = df[df["mes"] == mes].copy()

            # Agregar úteis e fds dentro do mês
            df_uteis = df_mes[df_mes["eh_fds"] == False]
            df_fds = df_mes[df_mes["eh_fds"] == True]

            agg_uteis = df_uteis.groupby(df_uteis.index)[colunas_perfil].mean()
            agg_fds = df_fds.groupby(df_fds.index)[colunas_perfil].mean()
            agg_uteis.columns = [f"uteis_{c}" for c in agg_uteis.columns]
            agg_fds.columns = [f"fds_{c}" for c in agg_fds.columns]

            perfil_mes = agg_uteis.join(agg_fds, how="outer").fillna(0)

            # Normalizar L1
            soma = perfil_mes.sum(axis=1)
            perfil_norm = perfil_mes.div(soma, axis=0)

            # Rodar K-Means para este mês
            kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
            grupos = kmeans.fit_predict(perfil_norm)

            # Interpretar grupos (qual é comercial?)
            razao_mes = df_mes.groupby(df_mes.index)["razao_comercial"].mean()
            perfil_mes["razao_comercial"] = razao_mes
            perfil_mes["grupo"] = grupos

            razao_por_grupo = perfil_mes.groupby("grupo")["razao_comercial"].mean()
            grupo_comercial = razao_por_grupo.idxmax()
            grupo_residencial = razao_por_grupo.idxmin()

            # Mapear e guardar o voto
            for mac, row in perfil_mes.iterrows():
                if mac not in votos_por_router:
                    votos_por_router[mac] = []
                if row["grupo"] == grupo_comercial:
                    votos_por_router[mac].append("comercial")
                else:
                    votos_por_router[mac].append("residencial")

        # Contar votos e definir classificação final (moda)
        classificacao_final = {}
        for mac, votos in votos_por_router.items():
            # Pega o voto mais frequente
            classificacao_final[mac] = max(set(votos), key=votos.count)

        # Criar DataFrame final com a classificação votada
        df_final = pd.DataFrame.from_dict(classificacao_final, orient="index", columns=["classificacao_kmeans"])
        df_final.index.name = "router_mac"

        # Adicionar razao_comercial média (para a regra)
        if "razao_comercial" in df.columns:
            df_final["razao_comercial"] = df.groupby(df.index)["razao_comercial"].mean()

        # Adicionar perfis médios (para visualização)
        agg_uteis = df[df["eh_fds"] == False].groupby(level=0)[colunas_perfil].mean()
        agg_fds = df[df["eh_fds"] == True].groupby(level=0)[colunas_perfil].mean()
        agg_uteis.columns = [f"uteis_{c}" for c in agg_uteis.columns]
        agg_fds.columns = [f"fds_{c}" for c in agg_fds.columns]
        perfis_medios = agg_uteis.join(agg_fds, how="outer").fillna(0)
        df_final = df_final.join(perfis_medios)

        # Hora de pico
        colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
        if all(c in df_final.columns for c in colunas_uteis):
            df_final["hora_pico"] = df_final[colunas_uteis].idxmax(axis=1).str.replace("uteis_h_", "").astype(int)

        df = df_final
        print(f"[modelo] Após votação: {len(df)} roteadores únicos")
        print(f"[modelo] Features: {len(df.columns)} colunas")

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
    # 1. Selecionar as colunas do perfil horário
    # Se temos 2 perfis (úteis + fds), usar ambos. Senão, usar o perfil único.
    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]
    colunas_simples = [f"h_{i}" for i in range(24)]

    if all(c in df.columns for c in colunas_uteis):
        # Modo 2 perfis: úteis + fds (48 colunas)
        perfil = df[colunas_uteis + colunas_fds]
        print(f"[kmeans] Usando 2 perfis (úteis + fds): {len(perfil.columns)} colunas")
    else:
        # Modo 1 perfil (compatibilidade)
        perfil = df[colunas_simples]
        print(f"[kmeans] Usando 1 perfil: {len(perfil.columns)} colunas")

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

    Se houver 2 perfis (úteis + fds), mostra ambos separadamente
    para comparar o comportamento em dias úteis vs fins de semana.
    """
    df_com_grupos = df.copy()
    df_com_grupos["grupo"] = grupos

    # Verificar se temos 2 perfis ou 1
    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]
    colunas_simples = [f"h_{i}" for i in range(24)]

    tem_2_perfis = all(c in df.columns for c in colunas_uteis)

    if tem_2_perfis:
        # Mostrar 2 perfis separadamente
        for tipo, colunas in [("DIAS ÚTEIS", colunas_uteis), ("FINS DE SEMANA", colunas_fds)]:
            print(f"\n[perfil] === {tipo} ===")
            perfil_medio = df_com_grupos.groupby("grupo")[colunas].mean()
            for g in perfil_medio.index:
                print(f"\n[perfil] Grupo {g}:")
                top5 = perfil_medio.loc[g].nlargest(5)
                for hora, valor in top5.items():
                    print(f"[perfil]   {hora}: {valor:,.0f} bytes")
    else:
        # Mostrar 1 perfil (compatibilidade)
        perfil_medio = df_com_grupos.groupby("grupo")[colunas_simples].mean()
        print(f"[perfil] Perfil horário médio por grupo:")
        for g in perfil_medio.index:
            print(f"\n[perfil] Grupo {g}:")
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

    # 0. Identificar outliers por PADRÃO PLANO (não por volume)
    # Depois da normalização L1, o volume não existe mais. O problema do
    # outlier é o PADRÃO: um roteador com tráfego igual em todas as horas
    # (perfil plano, sem pico) é anômalo e atrai um centroide só para ele.
    #
    # Como detectar perfil plano? Calculamos o desvio padrão (std) do
    # perfil normalizado. Perfil plano → std baixo. Perfil com pico → std alto.
    print("\n→ Passo 0: Identificando outliers (padrão plano)...")

    # Selecionar as colunas do perfil (depende do modo: 2 perfis ou 1)
    colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
    colunas_fds = [f"fds_h_{i}" for i in range(24)]
    colunas_simples = [f"h_{i}" for i in range(24)]

    if all(c in df.columns for c in colunas_uteis):
        # Modo 2 perfis: usar dias úteis para detectar padrão plano
        perfil = df[colunas_uteis]
        print("   Usando perfil de dias úteis para detectar outliers")
    else:
        # Modo 1 perfil
        perfil = df[colunas_simples]

    # Normalizar com L1 (cada perfil soma 1)
    soma_por_router = perfil.sum(axis=1)
    perfil_normalizado = perfil.div(soma_por_router, axis=0)

    # Calcular o std de cada perfil normalizado
    # Perfil plano: std ≈ 0 (todas as horas iguais)
    # Perfil com pico: std alto (umas horas muito maiores que outras)
    std_perfil = perfil_normalizado.std(axis=1)

    # Threshold: valor fixo baseado na análise dos dados.
    # O std médio dos perfis normais é ~0.035. Perfis planos (anômalos) têm std < 0.01.
    # Um valor de 0.01 significa que o tráfego varia muito pouco entre as horas
    # (menos de 1% de variação), indicando ausência de pico.
    threshold = 0.01
    mascara_outlier = std_perfil < threshold
    mascara_normal = ~mascara_outlier

    print(f"   Std médio dos perfis: {std_perfil.mean():.4f}")
    print(f"   Threshold (1º percentil): {threshold:.4f}")
    print(f"   Outliers (padrão plano): {mascara_outlier.sum()}")
    print(f"   Roteadores normais: {mascara_normal.sum()}")

    # Separar outliers e normais
    df_outliers = df[mascara_outlier].copy()
    df = df[mascara_normal].copy()

    # Classificar outliers como "padrao_anomalo"
    classificacao_outliers = pd.Series(
        "padrao_anomalo", index=df_outliers.index, name="classificacao_kmeans"
    )

    # 1. Regra de negócio
    print("\n" + "=" * 60)
    print("  ABORDAGEM 1: REGRA DE NEGÓCIO (baseline)")
    print("=" * 60)
    classificacao_regra = classificar_regra(df)

    # 2. K-Means (JÁ CALCULADO PELA VOTAÇÃO POR MÊS)
    print("\n" + "=" * 60)
    print("  ABORDAGEM 2: K-MEANS (Votação por mês)")
    print("=" * 60)
    # A coluna 'classificacao_kmeans' já foi preenchida pela votação no início do arquivo
    classificacao_kmeans = df["classificacao_kmeans"].copy()
    print(f"[kmeans] Total: {len(classificacao_kmeans)} roteadores")
    print(f"[kmeans] Comercial: {(classificacao_kmeans == 'comercial').sum()}")
    print(f"[kmeans] Residencial: {(classificacao_kmeans == 'residencial').sum()}")

    # 3. Comparar métodos
    print("\n" + "=" * 60)
    print("  COMPARAÇÃO: REGRA vs K-MEANS")
    print("=" * 60)
    comparacao = comparar_metodos(classificacao_regra, classificacao_kmeans)

    # 4. Analisar perfil horário
    print("\n" + "=" * 60)
    print("  PERFIL HORÁRIO POR GRUPO")
    print("=" * 60)
    # Usar a classificação final como grupo para plotar o perfil
    analisar_perfil_grupos(df, classificacao_kmeans)

    # 6. Salvar resultado final
    print("\n" + "=" * 60)
    print("  SALVANDO RESULTADOS")
    print("=" * 60)

    # Criar tabela final com as classificações
    resultado = df.copy()
    resultado["classificacao_regra"] = classificacao_regra
    resultado["classificacao_kmeans"] = classificacao_kmeans
    resultado["concorda"] = resultado["classificacao_regra"] == resultado["classificacao_kmeans"]

    # Adicionar os outliers classificados como "padrao_anomalo"
    resultado_outliers = df_outliers.copy()
    resultado_outliers["classificacao_regra"] = "padrao_anomalo"
    resultado_outliers["classificacao_kmeans"] = "padrao_anomalo"
    resultado_outliers["concorda"] = True  # ambos concordam que é anômalo

    # Juntar normais + outliers
    resultado = pd.concat([resultado, resultado_outliers])

    # Salvar
    os.makedirs("data/processed", exist_ok=True)
    resultado.to_csv("data/processed/classificacao_ia_2026-04-01.csv")
    print(f"✅ Resultado salvo em data/processed/classificacao_ia_2026-04-01.csv")
    print(f"   {len(resultado)} roteadores classificados")
    print(f"   - Normais: {len(df)}")
    print(f"   - Padrão anômalo: {len(df_outliers)}")

    # Resumo final
    print("\n" + "=" * 60)
    print("  RESUMO FINAL")
    print("=" * 60)
    print(f"  Regra de negócio (roteadores normais):")
    print(f"    Comercial:      {(classificacao_regra == 'comercial').sum()}")
    print(f"    Residencial:    {(classificacao_regra == 'residencial').sum()}")
    print(f"  K-Means (roteadores normais):")
    print(f"    Comercial:      {(classificacao_kmeans == 'comercial').sum()}")
    print(f"    Residencial:    {(classificacao_kmeans == 'residencial').sum()}")
    print(f"  Outliers (padrão anômalo): {len(df_outliers)}")
    concordancia = (classificacao_regra == classificacao_kmeans).mean() * 100
    print(f"  Concordância (normais):  {concordancia:.1f}%")
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