# Modelo Residencial/Comercial de Roteadores

Classificação de roteadores de internet como **residenciais** ou **comerciais** com base no padrão de tráfego de dados ao longo do tempo, a partir de dados do **QuestDB**.

## Metodologia

O tráfego é analisado por **horário do dia** (comercial: 8h–18h; residencial: 18h–8h) e por **tipo de dia** (dias úteis vs. fins de semana e feriados nacionais/estaduais do RJ). Duas abordagens rodam em paralelo:

1. **Regra de negócio (baseline, não é ML):** se >50% do tráfego ocorre em horário comercial em dias úteis → comercial; caso contrário → residencial.
2. **K-Means (clustering, ML não supervisionado):** agrupa roteadores por similaridade do perfil horário (dois perfis por roteador: dias úteis e fins de semana), com **votação por mês** para robustez contra meses atípicos.
3. **Concordância:** quando os dois métodos concordam (91,9% dos casos), a classificação tem alta confiança; discordâncias são investigadas caso a caso.

Roteadores com perfil horário plano (sem pico de tráfego, baixo desvio padrão do perfil normalizado) são classificados separadamente como `padrao_anomalo`.

## Fontes de dados

Dados armazenados no **QuestDB**, extraídos via PostgreSQL wire (porta 8812):

| Tabela | Descrição |
| --- | --- |
| routers | Dados de localização dos roteadores (série temporal, deduplicada por timestamp mais recente) |
| device_metrics | Tráfego dos dispositivos (granularidade de 1 minuto) |

- Período histórico: ~120 dias (abril em diante)
- Roteadores únicos: ~6.016 (12.177 linhas com duplicatas)
- Colunas de `routers`: router_mac, timestamp, manufacturer, model, user_ppp, location, city, state, latitude, longitude
- Colunas de `device_metrics`: device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down

## Estrutura do projeto

```
modelo_residencial_comercial/
├── extracao.py                        # Etapa 2: extração do QuestDB (extrair, processar, deletar)
├── eda.py                             # Etapa 3: EDA da tabela routers
├── eda_metrics.py                     # Etapa 3: EDA da tabela device_metrics
├── features.py                        # Etapa 4: engenharia de features (múltiplos dias)
├── modelo_ia.py                       # Etapa 5: modelagem (regra + K-Means com votação por mês)
├── modelo_hdbscan_ia.py              # Etapa 5: modelagem alternativa (HDBSCAN)
├── avaliacao_ia.py                    # Etapa 6: avaliação com localização
├── graficos_ia.py                     # Etapa 6: geração de gráficos
├── comparacao_humana_ia.py            # Etapa 6: comparação com análise humana (Grafana)
├── validacao_manual_ia.py             # Etapa 6: validação manual (20 endereços)
├── analise_volume_sazonalidade_ia.py  # Etapa 6: análise de volume e sazonalidade
├── teste_normalizacao_ia.py           # Etapa 6: teste de normalizações (L1, L2, Z-Score)
├── pipeline_ia.py                     # Etapa 7: pipeline automatizado
├── data/
│   ├── raw/                           # dados brutos (temporários, deletados após processar)
│   └── processed/                     # features e classificações (pequenos, permanentes)
│       └── graficos/                  # gráficos PNG gerados
├── graficos/                          # cópia dos gráficos PNG
├── docs/                              # documentação oficial
│   ├── projeto.md                     # documentação técnica
│   ├── relatorio_final.md             # relatório final de insights
│   └── referencia.md                  # teoria e referências
└── readme.md                          # este arquivo
```

## Como funciona

1. **Coleta (`extracao.py`):** extrai os dados do QuestDB dia a dia. Para cada dia: extrai → processa features → deleta o dado bruto (Opção B, economiza disco).
2. **EDA (`eda.py`, `eda_metrics.py`):** exploração pré-modelagem — faltantes, distribuições, outliers, tipos de colunas.
3. **Features (`features.py`):** transforma bytes acumulados em tráfego real por minuto (diff), agrupa por roteador e hora e calcula: tráfego comercial (8h–18h) e residencial (18h–8h) em dias úteis, razão comercial, hora de pico e perfil horário (`h_0` a `h_23`).
4. **Modelagem (`modelo_ia.py`):** aplica regra e K-Means, detecta outliers por padrão plano e salva a classificação final.
5. **Avaliação:** cruzamento com endereços/localização da tabela `routers` — endereços comerciais devem corresponder a roteadores classificados como comerciais.

### Estratégia de processamento (Opção B)

Para lidar com o volume (~180 GB em CSV para 4 meses), o processamento é incremental:

```
Para cada dia:
  1. Extrair do QuestDB → CSV (~1,5 GB)
  2. Processar features → CSV (~1 MB)
  3. Deletar CSV bruto → libera disco
```

No final, as features são consolidadas em um único arquivo (~120 MB para 4 meses).

## Uso

```bash
# Pipeline completo
python pipeline_ia.py

# Ou etapa por etapa
python extracao.py
python features.py
python modelo_ia.py
python avaliacao_ia.py
python graficos_ia.py
```

## Resultados (111 dias, 5.650 roteadores)

| Métrica | Valor |
| --- | --- |
| Roteadores analisados | 5.650 |
| Comerciais | 453 (8,0%) |
| Residenciais | 5.135 (90,9%) |
| Padrão anômalo | 62 (1,1%) |
| Concordância regra vs K-Means | 91,9% |
| Silhouette Score | 0,4711 |
| Validação humana (Grafana) | 100% (4/4) |

## Avaliação

1. **Validação humana (Grafana):** 4 roteadores analisados visualmente — 100% de acerto.
2. **Validação manual (endereços):** 20 roteadores verificados no Google Maps (`validacao_manual_ia.py`). Indicadores: "CASA"/"Ap." = residencial; "LOJA"/"sala" = comercial.
3. **Comparação regra vs K-Means:** 91,9% de concordância.

### Gráficos

Os gráficos estão em `graficos/` (ou `data/processed/graficos/`):

- **`04_perfil_horario_comparativo.png`** — perfil horário: comercial vs residencial, úteis vs fds (gráfico mais importante)
- **`06_volume_boxplot.png`** — distribuição de volume total por grupo (detalhes na Seção 5.2 de `docs/relatorio_final.md`)

## Descobertas da EDA

- Tabela `routers` é série temporal — deduplicação pelo timestamp mais recente
- Fabricante: todos TP-Link (variável constante, sem valor para o modelo)
- Localização: RJ, concentrados em Nova Friburgo e região dos lagos; 66% sem localização
- 2 roteadores com latitude inválida (-227, erro de digitação)
- `bytes_up`/`bytes_down` são contadores acumulados, não tráfego por minuto
- `last_connected`: 100% nulo, removido da extração
- Sazonalidade: dias úteis vs fins de semana, férias escolares (jun/jul), Copa do Mundo 2026
