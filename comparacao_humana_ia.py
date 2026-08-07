"""
comparacao_humana_ia.py — Comparação: Análise Humana vs Modelo
============================================================

Compara a classificação feita manualmente (análise no Grafana)
com a classificação do modelo (regra e K-Means).

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd

# ============================================================
# Análise humana (feita no Grafana)
# ============================================================
# Classificação manual de 4 roteadores baseada em observação visual
# do tráfego de bytes no Grafana.
ANALISE_HUMANA = {
    "0c:ef:15:08:bd:60": {
        "classificacao": "comercial",
        "justificativa": "Fds praticamente sem tráfego, tráfego baixo entre 18h-06h"
    },
    "3c:6a:d2:a6:f3:50": {
        "classificacao": "residencial",
        "justificativa": "Tráfego constante, pico fora do horário comercial"
    },
    "0c:ef:15:be:97:e0": {
        "classificacao": "residencial",
        "justificativa": "Tráfego constante"
    },
    "0c:ef:15:07:a3:60": {
        "classificacao": "residencial",
        "justificativa": "Tráfego constante, pico fora do comercial, alto fluxo no fds"
    },
}


def main():
    """Compara a análise humana com a classificação do modelo."""
    print("=" * 60)
    print("  COMPARAÇÃO: ANÁLISE HUMANA vs MODELO")
    print("=" * 60)

    # Carregar classificação do modelo
    try:
        df = pd.read_csv(
            "data/processed/classificacao_ia_2026-04-01.csv",
            index_col="router_mac"
        )
    except FileNotFoundError:
        print("❌ Arquivo de classificação não encontrado!")
        print("   Rode o modelo_ia.py primeiro.")
        return

    print(f"\n→ Modelo carregado: {len(df)} roteadores classificados\n")

    # Comparar cada roteador
    print(f"{'='*80}")
    print(f"{'Router MAC':<20} {'Humana':<15} {'Regra':<15} {'K-Means':<15} {'Acertou?'}")
    print(f"{'='*80}")

    acertos_regra = 0
    acertos_kmeans = 0
    total = 0

    for mac, info_humana in ANALISE_HUMANA.items():
        classificacao_humana = info_humana["classificacao"]
        justificativa = info_humana["justificativa"]

        # Buscar no modelo
        if mac in df.index:
            classificacao_regra = df.loc[mac, "classificacao_regra"]
            classificacao_kmeans = df.loc[mac, "classificacao_kmeans"]
            razao = df.loc[mac, "razao_comercial"]

            # Verificar acertos
            acertou_regra = "✅" if classificacao_humana == classificacao_regra else "❌"
            acertou_kmeans = "✅" if classificacao_humana == classificacao_kmeans else "❌"

            if classificacao_humana == classificacao_regra:
                acertos_regra += 1
            if classificacao_humana == classificacao_kmeans:
                acertos_kmeans += 1
            total += 1

            print(f"{mac:<20} {classificacao_humana:<15} {classificacao_regra:<15} "
                  f"{classificacao_kmeans:<15} R:{acertou_regra} K:{acertou_kmeans}")

            # Detalhes
            print(f"  → Justificativa humana: {justificativa}")
            print(f"  → Razão comercial do modelo: {razao:.4f}")
            print()
        else:
            print(f"{mac:<20} {classificacao_humana:<15} {'NÃO ENCONTRADO':<15} {'NÃO ENCONTRADO':<15}")
            print(f"  → Justificativa humana: {justificativa}")
            print(f"  → ⚠️ Roteador não está no arquivo de classificação")
            print()

    # Resumo
    print(f"{'='*60}")
    print(f"  RESUMO")
    print(f"{'='*60}")
    print(f"  Total analisado: {total}")
    print(f"  Acertos da regra: {acertos_regra}/{total} ({acertos_regra/total*100:.1f}%)" if total > 0 else "")
    print(f"  Acertos do K-Means: {acertos_kmeans}/{total} ({acertos_kmeans/total*100:.1f}%)" if total > 0 else "")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()