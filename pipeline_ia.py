"""
pipeline_ia.py — Pipeline Automatizado (Etapa 7)
============================================================
ETAPA 7 DO PROJETO: DEPLOY
============================================================

Este arquivo orquestra todo o pipeline de dados, rodando
todas as etapas em sequência:

  1. extracao.py    → extrai dados do QuestDB e processa features
  2. modelo_ia.py   → classifica roteadores (regra + K-Means)
  3. avaliacao_ia.py → valida com localização
  4. graficos_ia.py → gera gráficos

COMO USAR:
  python pipeline_ia.py

  O script vai rodar tudo em sequência e gerar:
  - data/processed/features_todos_dias.csv
  - data/processed/classificacao_ia_2026-04-01.csv
  - data/processed/avaliacao_ia_2026-04-01.csv
  - data/processed/graficos/*.png
  - data/processed/mapa_classificacao.html

IMPORTANTE: este arquivo foi gerado por IA (GitHub Copilot).
============================================================
"""

import time
import sys
import os


def main():
    """Executa todo o pipeline em sequência."""
    inicio = time.time()

    print("=" * 60)
    print("  PIPELINE AUTOMATIZADO — MODELO RESIDENCIAL/COMERCIAL")
    print("=" * 60)
    print(f"  Início: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Lista de etapas (módulo, nome, função)
    etapas = [
        ("extracao", "Extração e Features", "main"),
        ("modelo_ia", "Modelagem (Regra + K-Means)", "main"),
        ("avaliacao_ia", "Avaliação com Localização", "main"),
        ("graficos_ia", "Geração de Gráficos", "main"),
    ]

    # Executar cada etapa
    for i, (modulo, nome, funcao) in enumerate(etapas, 1):
        print(f"\n{'='*60}")
        print(f"  ETAPA {i}/4: {nome}")
        print(f"{'='*60}")

        etapa_inicio = time.time()

        try:
            # Importar o módulo
            print(f"→ Importando {modulo}...")
            mod = __import__(modulo)

            # Executar a função principal
            print(f"→ Executando {modulo}.{funcao}()...")
            getattr(mod, funcao)()

            etapa_tempo = time.time() - etapa_inicio
            print(f"\n✅ Etapa {i} concluída em {etapa_tempo:.1f}s")

        except Exception as e:
            print(f"\n❌ Erro na etapa {i} ({modulo}): {e}")
            print(f"   Pipeline interrompido.")
            return

    # Resumo final
    tempo_total = time.time() - inicio
    print(f"\n{'='*60}")
    print(f"  PIPELINE CONCLUÍDO!")
    print(f"{'='*60}")
    print(f"  Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} min)")
    print(f"  Fim: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"  Arquivos gerados:")
    print(f"    - data/processed/features_todos_dias.csv")
    print(f"    - data/processed/classificacao_ia_2026-04-01.csv")
    print(f"    - data/processed/avaliacao_ia_2026-04-01.csv")
    print(f"    - data/processed/graficos/*.png")
    print(f"    - data/processed/mapa_classificacao.html")
    print(f"{'='*60}")


# ============================================================
# Executa se o arquivo for chamado diretamente
# python pipeline_ia.py
# ============================================================
if __name__ == "__main__":
    main()