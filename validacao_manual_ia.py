"""
validacao_manual_ia.py — Validação Manual (Ground Truth)
============================================================
ETAPA 6 DO PROJETO: AVALIAÇÃO COM GROUND TRUTH MANUAL
============================================================

Compara a classificação do modelo com a análise manual de 20 roteadores,
feita olhando os endereços no Google Maps.

METODOLOGIA:
  1. O script de amostra gerou 20 roteadores (10 com alta razão comercial,
     10 com baixa razão comercial).
  2. A usuária pesquisou cada endereço na internet e olhou no Street View
     do Google Maps para classificar manualmente:
     - "CASA", "casa", "Ap.", "lot" → RESIDENCIAL
     - "LOJA", "sala", "IMOBILIÁRIA" → COMERCIAL
     - Quando não dava para identificar como comercial → RESIDENCIAL
     - Alguns residenciais podem ser Airbnb, mas foram considerados residencial
  3. Este script compara a classificação manual com o modelo (regra e K-Means).

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import pandas as pd

# ============================================================
# Classificação manual (ground truth) — 20 roteadores
# ============================================================
# Cada roteador foi classificado pesquisando o endereço na internet e
# olhando no Street View do Google Maps.
# Indicadores usados:
#   - "CASA", "casa", "Ap.", "lot" → RESIDENCIAL
#   - "LOJA", "loja", "sala", "sla", "IMOBILIÁRIA" → COMERCIAL
#   - Quando não dava para identificar como comercial → RESIDENCIAL
#   - Alguns residenciais podem ser Airbnb, mas foram considerados residencial
#
# A primeira amostra (e0:d3:62:62:c3:f0) foi confirmada pela usuária
# como RESIDENCIAL (endereço diz "CASA" mas modelo classificou como comercial).

ANALISE_MANUAL = {
    # --- AMOSTRA COMERCIAL (alta razão comercial — modelo diz comercial) ---
    "e0:d3:62:62:c3:f0": {
        "classificacao": "residencial",
        "endereco": "Rua Prudente de Morais, 270 CASA - Vila Nova - Nova Friburgo",
        "justificativa": "Endereço diz 'CASA' — é residencial, não comercial"
    },
    "98:ba:5f:f7:fa:f8": {
        "classificacao": "comercial",
        "endereco": "Avenida Lúcio Meira, 112 - Várzea - Teresópolis",
        "justificativa": "Avenida, sem indicador residencial — comercial confirmado no Street View"
    },
    "50:3d:d1:1f:2b:70": {
        "classificacao": "comercial",
        "endereco": "Avenida Nilo Peçanha, 188 BELLA CASA IMOBILIÁRIA - Centro - Cabo Frio",
        "justificativa": "Endereço diz 'IMOBILIÁRIA' — comércio confirmado"
    },
    "e0:d3:62:63:46:e0": {
        "classificacao": "comercial",
        "endereco": "Av. Getúlio Vargas, 644 - Vila Canaã - Arraial do Cabo",
        "justificativa": "Avenida, sem indicador residencial — comercial confirmado no Street View"
    },
    "50:3d:d1:1f:81:f0": {
        "classificacao": "comercial",
        "endereco": "Av. Gov. Leonel de Moura Brizola, 50 - Praia Grande - Arraial do Cabo",
        "justificativa": "Avenida, sem indicador residencial — comercial confirmado no Street View"
    },
    "3c:6a:d2:a6:e9:50": {
        "classificacao": "residencial",
        "endereco": "Rua Romão Aguilera Campos, 1030 Bloco 19 Ap. 102 - Olaria - Nova Friburgo",
        "justificativa": "Endereço diz 'Ap. 102' — é apartamento residencial"
    },
    "50:3d:d1:5d:69:e8": {
        "classificacao": "comercial",
        "endereco": "Rua Duque de Caxias, S/Nº loja 01 - Centro - Nova Friburgo",
        "justificativa": "Endereço diz 'loja 01' — comércio confirmado"
    },
    "e0:d3:62:63:bc:98": {
        "classificacao": "residencial",
        "endereco": "Alameda Iracema, 801 casa 6 - Granja Guarani - Teresópolis",
        "justificativa": "Endereço diz 'casa 6' — é residencial"
    },
    "e0:d3:62:63:e7:c8": {
        "classificacao": "comercial",
        "endereco": "Rua Nossa Senhora de Fátima, 42 LOJA B - Centro - Nova Friburgo",
        "justificativa": "Endereço diz 'LOJA B' — comércio confirmado"
    },
    "50:3d:d1:5d:79:38": {
        "classificacao": "comercial",
        "endereco": "Waldir Barbosa Moreira, 205 sla 205 - Várzea - Teresópolis",
        "justificativa": "Endereço diz 'sla 205' (sala) — é sala comercial"
    },

    # --- AMOSTRA RESIDENCIAL (baixa razão comercial — modelo diz residencial) ---
    "50:3d:d1:1f:2f:b0": {
        "classificacao": "residencial",
        "endereco": "Rua Presidente Raul Veiga, 211 - Olaria - Nova Friburgo",
        "justificativa": "Rua residencial, sem indicador comercial — residencial"
    },
    "8c:86:dd:88:33:30": {
        "classificacao": "residencial",
        "endereco": "Rua Alberto de Oliveira, 110 casa - São Pedro - Teresópolis",
        "justificativa": "Endereço diz 'casa' — residencial confirmado"
    },
    "bc:07:1d:0d:e5:b0": {
        "classificacao": "residencial",
        "endereco": "Rua 3, 115 CASA - ALTO DO RETIRO - Retiro Poetico - Cordeiro",
        "justificativa": "Endereço diz 'CASA' — residencial confirmado"
    },
    "8c:86:dd:88:2d:a8": {
        "classificacao": "residencial",
        "endereco": "RJ-142, S/Nº Poço Feio - KM 22 - Lumiar - Nova Friburgo",
        "justificativa": "Zona rural (KM 22) — residencial confirmado"
    },
    "e0:d3:62:63:c2:b8": {
        "classificacao": "residencial",
        "endereco": "Rua Dallas, 137 Casa - Macedônia - Arraial do Cabo",
        "justificativa": "Endereço diz 'Casa' — residencial (possível Airbnb)"
    },
    "98:ba:5f:f8:7b:c0": {
        "classificacao": "residencial",
        "endereco": "Rua Manoel Neto, S/Nº lot 11 - Maria Joaquina - Armação dos Búzios",
        "justificativa": "Endereço diz 'lot 11' (lote) — residencial (possível Airbnb)"
    },
    "8c:86:dd:88:31:a0": {
        "classificacao": "residencial",
        "endereco": "Rua Padre Tintorio, 179 CASA 04 - Várzea - Teresópolis",
        "justificativa": "Endereço diz 'CASA 04' — residencial confirmado"
    },
    "bc:07:1d:0e:4d:10": {
        "classificacao": "residencial",
        "endereco": "Rua Waldemar de Assis Ribeiro, 133 CASA 05 - Cascata Guarani - Teresópolis",
        "justificativa": "Endereço diz 'CASA 05' — residencial confirmado"
    },
    "98:03:8e:25:83:78": {
        "classificacao": "residencial",
        "endereco": "Rua Martins Afonso, 87 Praia Grande - Centro - Arraial do Cabo",
        "justificativa": "Rua, sem indicador comercial — residencial (possível Airbnb)"
    },
    "50:3d:d1:1f:32:10": {
        "classificacao": "residencial",
        "endereco": "Rua Dos Namorados, 19 CASA - Geribá - Armação dos Búzios",
        "justificativa": "Endereço diz 'CASA' — residencial (possível Airbnb)"
    },
}


def main():
    """Compara a classificação manual com o modelo."""
    print("=" * 60)
    print("  VALIDAÇÃO MANUAL — GROUND TRUTH (20 ROTEADORES)")
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
    print(f"{'='*100}")
    print(f"{'Router MAC':<20} {'Manual':<14} {'Regra':<14} {'K-Means':<14} {'R':<4} {'K':<4} {'Razão':<8} {'Justificativa'}")
    print(f"{'='*100}")

    acertos_regra = 0
    acertos_kmeans = 0
    total = 0
    erros_regra = []
    erros_kmeans = []

    for mac, info in ANALISE_MANUAL.items():
        classificacao_manual = info["classificacao"]
        justificativa = info["justificativa"]

        if mac in df.index:
            classificacao_regra = df.loc[mac, "classificacao_regra"]
            classificacao_kmeans = df.loc[mac, "classificacao_kmeans"]
            razao = df.loc[mac, "razao_comercial"]

            acertou_regra = classificacao_manual == classificacao_regra
            acertou_kmeans = classificacao_manual == classificacao_kmeans

            if acertou_regra:
                acertos_regra += 1
            else:
                erros_regra.append((mac, classificacao_manual, classificacao_regra, razao))

            if acertou_kmeans:
                acertos_kmeans += 1
            else:
                erros_kmeans.append((mac, classificacao_manual, classificacao_kmeans, razao))

            total += 1

            simbolo_r = "✅" if acertou_regra else "❌"
            simbolo_k = "✅" if acertou_kmeans else "❌"

            # Truncar justificativa para caber na tela
            just = justificativa[:40]

            print(f"{mac:<20} {classificacao_manual:<14} {classificacao_regra:<14} "
                  f"{classificacao_kmeans:<14} {simbolo_r:<4} {simbolo_k:<4} {razao:<8.4f} {just}")
        else:
            print(f"{mac:<20} {classificacao_manual:<14} {'NÃO ENCONTRADO':<14} {'NÃO ENCONTRADO':<14}")
            print(f"  → {justificativa}")

    # Resumo
    print(f"\n{'='*60}")
    print(f"  RESUMO DA VALIDAÇÃO MANUAL")
    print(f"{'='*60}")
    print(f"  Total analisado:       {total}")
    print(f"  Acertos da regra:      {acertos_regra}/{total} ({acertos_regra/total*100:.1f}%)")
    print(f"  Acertos do K-Means:    {acertos_kmeans}/{total} ({acertos_kmeans/total*100:.1f}%)")
    print(f"{'='*60}")

    # Mostrar erros
    if erros_regra:
        print(f"\n→ Erros da REGRA ({len(erros_regra)}):")
        for mac, manual, regra, razao in erros_regra:
            print(f"  {mac}: manual={manual}, regra={regra}, razao={razao:.4f}")

    if erros_kmeans:
        print(f"\n→ Erros do K-MEANS ({len(erros_kmeans)}):")
        for mac, manual, kmeans, razao in erros_kmeans:
            print(f"  {mac}: manual={manual}, kmeans={kmeans}, razao={razao:.4f}")

    if not erros_regra and not erros_kmeans:
        print("\n🎉 PERFEITO! Nenhum erro — modelo acertou todos os 20 roteadores!")

    print(f"{'='*60}")


if __name__ == "__main__":
    main()