# Modelo Residencial Comercial

## Visão Geral

Este projeto é um modelo de classificação de roteadores em um banco de dados **QuestDB**. O modelo classifica os roteadores como **residenciais** ou **comerciais** com base no padrão de tráfego de dados ao longo do tempo.

## Metodologia

A classificação é baseada na análise do tráfego de dados considerando **dois fatores principais**:

1. **Horário do dia:**
   - **Período comercial:** das **8h às 18h**
   - **Período residencial:** fora do horário comercial (das 18h às 8h)

2. **Tipo de dia (Sazonalidade):**
   - **Dias úteis:** segunda a sexta (não feriados)
   - **Fins de semana e feriados:** sábado, domingo e feriados nacionais/estaduais (RJ)

### Critério de Classificação

O projeto usa **duas abordagens** em paralelo:

1. **Regra de negócio (baseline, NÃO é ML):** se a maioria do tráfego (>50%) ocorre no horário comercial (em dias úteis), o roteador é classificado como comercial. Caso contrário, residencial.

2. **K-Means (clustering, É ML — não supervisionado):** agrupa roteadores por similaridade do perfil horário. O modelo cria dois perfis para cada roteador (dias úteis e fins de semana) e usa uma **votação por mês** para definir a classificação final, garantindo robustez contra meses atípicos (ex: férias escolares, eventos esportivos).

3. **Comparação:** se os dois métodos concordam (91.9% dos casos), ganhamos confiança. Se discordam, investigamos os casos especiais.

### Detecção de outliers

Roteadores com padrão anômalo (perfil plano, sem pico de tráfego) são identificados pelo baixo desvio padrão do perfil normalizado e classificados separadamente como `padrao_anomalo`.

## Fontes de Dados

Os dados estão armazenados no **QuestDB** e são distribuídos em duas tabelas principais:

| Tabela           | Descrição                                     |
| ---------------- | --------------------------------------------- |
| `routers`        | Contém os dados de localização dos roteadores |
| `device_metrics` | Contém os dados de tráfego dos dispositivos   |

| Granularidade dos dados | A cada 1 minuto |
| Período histórico | Desde abril (~120 dias) |
| Número de roteadores | ~6.016 únicos (12.177 com duplicatas) |
| Volume estimado | ~15,8 milhões de linhas/dia |
| Colunas de `routers` | router_mac, timestamp, manufacturer, model, user_ppp, location, city, state, latitude, longitude |
| Colunas de `device_metrics` | device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down |

## Descobertas da EDA (Etapa 3)

- **Roteadores:** 6.016 únicos (tabela `routers` é série temporal, deduplicada por timestamp mais recente)
- **Fabricante:** todos TP-Link (variável constante, sem valor para o modelo)
- **Localização:** todos no RJ, concentrados em Nova Friburgo e região dos lagos
- **Dados faltantes:** 66% dos roteadores sem localização (validação será com os 34% que têm)
- **Latitude inválida:** 2 roteadores com latitude impossível (-227, provável erro de digitação)
- **Bytes acumulados:** `bytes_up` e `bytes_down` são contadores acumulados, não tráfego por minuto
- **`last_connected`:** 100% nulo, removido da extração
- **Sazonalidade:** considerar dias úteis vs fins de semana, férias escolares (jun/jul) e Copa do Mundo 2026

## Estrutura do Projeto

```
Modelo_localizacao_roteadores/
├── extracao.py                    # Etapa 2: extração do QuestDB (extrair, processar, deletar)
├── eda.py                         # Etapa 3: EDA da tabela routers
├── eda_metrics.py                 # Etapa 3: EDA da tabela device_metrics
├── features.py                    # Etapa 4: engenharia de features (múltiplos dias)
├── modelo_ia.py                   # Etapa 5: modelagem (regra + K-Means com votação por mês)
├── modelo_hdbscan_ia.py           # Etapa 5: modelagem alternativa (HDBSCAN)
├── avaliacao_ia.py                # Etapa 6: avaliação com localização
├── graficos_ia.py                 # Etapa 6: geração de gráficos
├── comparacao_humana_ia.py        # Etapa 6: comparação com análise humana (Grafana)
├── validacao_manual_ia.py         # Etapa 6: validação manual (20 endereços)
├── analise_volume_sazonalidade_ia.py  # Etapa 6: análise de volume e sazonalidade
├── teste_normalizacao_ia.py       # Etapa 6: teste de normalizações (L1, L2, Z-Score)
├── pipeline_ia.py                 # Etapa 7: pipeline automatizado
├── modelo.py                      # (vazio, reservado)
├── data/
│   ├── raw/                       # dados brutos (temporários, deletados após processar)
│   └── processed/                 # features e classificações (pequenos, permanentes)
│       └── graficos/              # gráficos PNG gerados
├── graficos/                      # cópia dos gráficos PNG
├── docs/                          # documentação
│   ├── projeto.md                 # documentação técnica
│   ├── referencia.md              # teoria e referências
│   └── prompt.md                  # prompt para IAs (modo professor)
├── readme.md                      # este arquivo
├── relatorio_final_ia.md          # relatório final de insights
├── material_estudo.md             # material teórico (ML, estatística, K-Means)
└── feedback.md                    # feedback do professor
```

## Como Funciona

1. **Coleta de dados (`extracao.py`):** extrai os dados do QuestDB dia a dia. Para cada dia, processa as features e deleta o dado bruto (Opção B — economiza disco).

2. **Análise exploratória (`eda.py`, `eda_metrics.py`):** explora os dados antes de modelar. Verifica dados faltantes, distribuições, outliers, tipos de colunas.

3. **Engenharia de features (`features.py`):** transforma os bytes acumulados em tráfego real por minuto (diff), agrupa por roteador e hora, calcula:
   - Tráfego comercial (8h-18h) e residencial (18h-7h)
   - Razão comercial (proporção do tráfego que é comercial)
   - Hora de pico
   - Perfil horário (24 valores: h_0 a h_23)
   - Dia da semana e flag de fim de semana

4. **Modelagem (`modelo_ia.py`):** aplica as duas abordagens (regra e K-Means) e compara. Identifica outliers por padrão plano. Salva a classificação final.

5. **Avaliação:** a validação será feita verificando a localização dos roteadores (cruzando com a tabela `routers`), avaliando se endereços comerciais correspondem a roteadores classificados como comerciais.

## Estratégia de processamento (Opção B)

Para lidar com o volume de dados (~180GB em CSV para 4 meses), usamos processamento incremental:

```
Para cada dia:
  1. Extrair do QuestDB → CSV (1,5 GB)
  2. Processar features → CSV (1 MB)
  3. Deletar CSV bruto → libera disco
```

No final, todas as features são consolidadas em um único arquivo (~120 MB para 4 meses).

## Avaliação

A avaliação foi feita de três formas:

1. **Validação humana (Grafana):** 4 roteadores analisados visualmente no Grafana. Resultado: 100% de acerto (regra e K-Means).

2. **Validação manual (endereços):** 20 roteadores analisados olhando o endereço no Google Maps. O script `validacao_manual_ia.py` faz a comparação. Indicadores usados: "CASA"/"Ap." = residencial, "LOJA"/"sala" = comercial.

3. **Comparação regra vs K-Means:** 91.9% de concordância entre os dois métodos. Quando concordam, ganhamos confiança. Quando discordam, investigamos caso a caso.

### Resultados (111 dias, 5.650 roteadores)

| Métrica                       | Valor         |
| ----------------------------- | ------------- |
| Roteadores analisados         | 5.650         |
| Comerciais                    | 453 (8.0%)    |
| Residenciais                  | 5.135 (90.9%) |
| Padrão anômalo                | 62 (1.1%)     |
| Concordância regra vs K-Means | 91.9%         |
| Silhouette Score              | 0.4711        |
| Validação humana (Grafana)    | 100% (4/4)    |

### Gráficos

Os gráficos estão em `graficos/` (ou `data/processed/graficos/`). Os mais importantes:

- **`04_perfil_horario_comparativo.png`** — perfil horário: comercial vs residencial, úteis vs fds (o gráfico mais importante do projeto)
- **`06_volume_boxplot.png`** — distribuição de volume total por grupo (ver Seção 5.2 do relatório final)
- **`08_por_cidade.png`** — comercial vs residencial por cidade
