"""
teste_normalizacao_ia.py — Teste de Normalizações (Prioridade 2)
============================================================

Testa diferentes formas de normalizar o perfil horário para verificar
se o K-Means está agrupando por volume ou por padrão.

Normalizações testadas:
1. L1 (atual) — divide pela soma (cada perfil soma 1)
2. L2 — divide pela raiz da soma dos quadrados
3. Z-Score (StandardScaler por linha) — média=0, desvio=1 por roteador

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import os

# ============================================================
# Carregar dados
# ============================================================
print("[teste] Carregando dados...")
df = pd.read_csv(
    "data/processed/classificacao_ia_2026-04-01.csv",
    index_col="router_mac"
)

# Selecionar colunas do perfil
colunas_uteis = [f"uteis_h_{i}" for i in range(24)]
colunas_fds = [f"fds_h_{i}" for i in range(24)]
perfil = df[colunas_uteis + colunas_fds]

# Calcular volume total para análise
df["volume_total"] = perfil.sum(axis=1)

# Remover outliers (padrão anômalo) para focar nos grupos principais
df_normal = df[df["classificacao_kmeans"] != "padrao_anomalo"].copy()
perfil_normal = perfil.loc[df_normal.index]


# ============================================================
# Função para rodar K-Means e analisar volume
# ============================================================
def testar_normalizacao(nome, perfil_norm):
    """Roda K-Means com uma normalização e analisa o volume dos grupos."""
    print(f"\n{'='*60}")
    print(f"  TESTE: {nome}")
    print(f"{'='*60}")

    # Rodar K-Means
    kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
    grupos = kmeans.fit_predict(perfil_norm)

    # Adicionar grupos ao DataFrame
    df_teste = df_normal.copy()
    df_teste["grupo"] = grupos

    # Identificar qual grupo é comercial (maior razao_comercial)
    razao_grupo = df_teste.groupby("grupo")["razao_comercial"].mean()
    grupo_comercial = razao_grupo.idxmax()
    grupo_residencial = razao_grupo.idxmin()

    # Mapear
    df_teste["classe"] = df_teste["grupo"].map({
        grupo_comercial: "comercial",
        grupo_residencial: "residencial"
    })

    # Calcular Silhouette
    silhouette = silhouette_score(perfil_norm, grupos)

    # Calcular volume médio por grupo
    vol_com = df_teste[df_teste["classe"] == "comercial"]["volume_total"].mean() / 1e9
    vol_res = df_teste[df_teste["classe"] == "residencial"]["volume_total"].mean() / 1e9

    # Tamanho dos grupos
    qtd_com = (df_teste["classe"] == "comercial").sum()
    qtd_res = (df_teste["classe"] == "residencial").sum()

    print(f"  Silhouette Score: {silhouette:.4f}")
    print(f"  Tamanho: Comercial={qtd_com}, Residencial={qtd_res}")
    print(f"  Volume médio (GB):")
    print(f"    Comercial:   {vol_com:.2f}")
    print(f"    Residencial: {vol_res:.2f}")
    print(f"    Razão Res/Com: {vol_res/vol_com:.2f}x")

    if vol_res > vol_com * 1.5:
        print(f"  ⚠️ Ainda há diferença de volume (Residencial é {vol_res/vol_com:.1f}x maior).")
    else:
        print(f"  ✅ Volumes parecidos! O K-Means está agrupando pelo padrão, não pelo volume.")

    return silhouette, vol_res / vol_com


# ============================================================
# 1. Normalização L1 (Atual)
# ============================================================
print("\n→ Calculando L1...")
soma = perfil_normal.sum(axis=1)
perfil_l1 = perfil_normal.div(soma, axis=0)
sil_l1, razao_l1 = testar_normalizacao("L1 (Atual)", perfil_l1)


# ============================================================
# 2. Normalização L2
# ============================================================
print("\n→ Calculando L2...")
soma_quadrados = np.sqrt((perfil_normal ** 2).sum(axis=1))
perfil_l2 = perfil_normal.div(soma_quadrados, axis=0)
sil_l2, razao_l2 = testar_normalizacao("L2", perfil_l2)


# ============================================================
# 3. Normalização Z-Score (StandardScaler por linha)
# ============================================================
print("\n→ Calculando Z-Score (por linha)...")
# Subtrai a média de cada roteador e divide pelo desvio padrão
media = perfil_normal.mean(axis=1)
std = perfil_normal.std(axis=1)
# Evitar divisão por zero
std = std.replace(0, 1)
perfil_zscore = perfil_normal.sub(media, axis=0).div(std, axis=0)
sil_zscore, razao_zscore = testar_normalizacao("Z-Score (por linha)", perfil_zscore)


# ============================================================
# Resumo Final
# ============================================================
print(f"\n{'='*60}")
print(f"  RESUMO DOS TESTES")
print(f"{'='*60}")
print(f"{'Normalização':<20} {'Silhouette':<15} {'Razão Vol (Res/Com)':<20}")
print(f"{'-'*55}")
print(f"{'L1 (Atual)':<20} {sil_l1:<15.4f} {razao_l1:<20.2f}x")
print(f"{'L2':<20} {sil_l2:<15.4f} {razao_l2:<20.2f}x")
print(f"{'Z-Score (por linha)':<20} {sil_zscore:<15.4f} {razao_zscore:<20.2f}x")
print(f"{'='*60}")

print("\n→ Como interpretar:")
print("  - Silhouette MAIOR = grupos melhores separados")
print("  - Razão Vol MAIS PRÓXIMA DE 1.0 = menos viés de volume")
print("  - Se Z-Score tiver razão perto de 1.0, ele é o melhor para remover o viés de volume.")