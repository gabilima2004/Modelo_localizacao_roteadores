# Documentação Técnica do Projeto

> Manual do desenvolvedor: detalhes técnicos, EDA e funcionamento interno.

# 1. Visão Geral

## Objetivo

Classificar roteadores de internet como **residenciais** ou **comerciais** com base no padrão de tráfego de dados ao longo do tempo.

## Status das etapas

| Etapa | Status | Arquivo principal |
| --- | --- | --- |
| 1. Definição do Problema | ✅ Concluída | `readme.md` |
| 2. Coleta de Dados | ✅ Concluída | `extracao.py` |
| 3. EDA | ✅ Concluída | `eda.py`, `eda_metrics.py` |
| 4. Engenharia de Features | ✅ Concluída | `features.py` |
| 5. Modelagem | ✅ Concluída | `modelo_ia.py` |
| 6. Avaliação | ✅ Concluída | `avaliacao_ia.py`, `graficos_ia.py` |
| 7. Interpretação & Deploy | ✅ Concluída | `docs/relatorio_final.md`, `pipeline_ia.py` |

## Estrutura de arquivos

Consulte a seção "Estrutura do projeto" do `readme.md`.

# 2. EDA (Análise Exploratória de Dados)

## EDA da tabela `routers` (`eda.py`)

- 12.177 linhas, mas só ~6.012 roteadores únicos (duplicatas)
- A tabela é série temporal (possui timestamp), não estática
- Solução: deduplicação pegando a versão mais recente com endereço
- 66% dos roteadores sem localização
- 2 roteadores com latitude inválida (-227, erro de digitação)
- Todos TP-Link, no RJ, concentrados em Nova Friburgo

## EDA da tabela `device_metrics` (`eda_metrics.py`)

- ~15,8 milhões de linhas por dia
- Cada linha é um device (média 1,7 devices/roteador)
- `bytes_up` e `bytes_down` são acumulados
- `last_connected`: 100% nulo, removido
- Dados faltantes: muito poucos nas colunas principais

# 3. Detalhamento por etapa

## Etapa 2: Coleta de Dados (`extracao.py`)

Extrai dados do QuestDB dia a dia. Usa a "Opção B": extrair, processar features, deletar dado bruto (economiza disco). Deduplica a tabela `routers` priorizando linhas com endereço.

Detalhes técnicos de conexão: ver `docs/referencia.md`.

## Etapa 4: Engenharia de Features (`features.py`)

Transforma bytes acumulados em tráfego real por minuto (diff), agrupa por roteador e hora, calcula:

- Tráfego comercial (8h-18h) e residencial (18h-8h) — só em dias úteis
- Razão comercial (proporção do tráfego em horário comercial)
- Hora de pico
- Perfil horário (24 valores: h_0 a h_23)
- Dia da semana, flag de fim de semana, flag de feriado, mês

Processa múltiplos dias e consolida em `features_todos_dias.csv`.

## Etapa 5: Modelagem (`modelo_ia.py`)

Aplica duas abordagens:

1. **Regra de negócio**: `razao_comercial > 0.5` → comercial
2. **K-Means**: agrupa por similaridade do perfil horário (48 colunas: úteis + fds)

**Detecção de outliers (padrão plano):** roteadores com perfil horário normalizado de baixo desvio padrão (abaixo do 1º percentil) são classificados como `padrao_anomalo`.

**Votação por mês:** o `features_todos_dias.csv` tem uma linha por roteador por dia; o K-Means roda para cada mês separadamente (2 perfis: dias úteis e fds) e a classificação final é a moda dos votos por mês. Um mês atípico (férias, eventos) não altera sozinho o resultado final.

**Normalização L1:** o perfil horário de cada roteador é dividido pela soma total, transformando-o em distribuição (soma 1). Assim o agrupamento usa a "forma" do tráfego, não o volume.

**Interpretação dos grupos:** o K-Means retorna grupos 0 e 1 sem rótulo; o grupo com maior média de `razao_comercial` é rotulado como comercial.

## Etapa 5 (alternativa): HDBSCAN (`modelo_hdbscan_ia.py`)

HDBSCAN testado como alternativa ao K-Means: não precisa de K, detecta outliers automaticamente (marca como -1/ruído) e suporta grupos de qualquer forma.

**Configuração**: PCA 3D (37,8% variância) + `min_cluster_size=50` + `min_samples=5`

**Resultado**: 2 grupos encontrados, mas muito conservador:

- Grupo 0 (comercial): 76 roteadores (vs 453 do K-Means)
- Grupo 1 (residencial): 4.948 roteadores
- Ruído: 626 roteadores (11%)
- Concordância com regra: 82,1% (vs 91,9% do K-Means)

**Conclusão**: HDBSCAN agrupou por padrão (horário do pico), mas é conservador demais. O K-Means é o melhor algoritmo porque o número de grupos é conhecido (2) e é preciso classificar todos os roteadores.

## Etapa 6: Avaliação (`avaliacao_ia.py`, `graficos_ia.py`, `comparacao_humana_ia.py`, `validacao_manual_ia.py`)

1. **Validação humana (Grafana)**: 4 roteadores analisados visualmente — 100% de acerto.
2. **Validação manual (endereços)**: 20 roteadores verificados no Google Maps (`validacao_manual_ia.py`). Indicadores: "CASA"/"Ap." = residencial; "LOJA"/"sala" = comercial.
3. **Comparação regra vs K-Means**: 91,9% de concordância (matriz via `pd.crosstab`).

Gráficos PNG em `data/processed/graficos/` (cópia em `graficos/`):

- `04_perfil_horario_comparativo.png` — perfil horário: comercial vs residencial, úteis vs fds (mais importante)
- `06_volume_boxplot.png` — distribuição de volume total por grupo
- `08_por_cidade.png` — comercial vs residencial por cidade
- Outros (distribuição, concordância, histograma, scatter)

Também gera mapa HTML com folium (localização dos roteadores).

## Etapa 7: Interpretação & Deploy (`docs/relatorio_final.md`, `pipeline_ia.py`)

- **Relatório final**: insights, limitações e recomendações (`docs/relatorio_final.md`)
- **Pipeline automatizado** (`pipeline_ia.py`): orquestra `extracao` → `modelo_ia` → `avaliacao_ia` → `graficos_ia` em sequência e registra o tempo de cada etapa.
