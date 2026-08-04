# Modelo Residencial Comercial

## Visão Geral

Este projeto é um modelo de classificação de roteadores em um banco de dados **QuestDB**. O modelo classifica os roteadores como **residenciais** ou **comerciais** com base no padrão de tráfego de dados ao longo do tempo.

## Metodologia

A classificação é baseada na análise do tráfego de dados por períodos do dia:

- **Período comercial:** das **8h às 18h**
- **Período residencial:** fora do horário comercial (das 18h às 8h)

### Critério de Classificação

O projeto usa **duas abordagens** em paralelo:

1. **Regra de negócio (baseline, NÃO é ML):** se a maioria do tráfego (>50%) ocorre no horário comercial, o roteador é classificado como comercial. Caso contrário, residencial.

2. **K-Means (clustering, É ML — não supervisionado):** agrupa roteadores por similaridade do perfil horário (24 valores de tráfego por hora). O algoritmo encontra os grupos sozinho; depois interpretamos qual grupo é comercial e qual é residencial.

3. **Comparação:** se os dois métodos concordam, ganhamos confiança. Se discordam, investigamos os casos especiais.

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
├── extracao.py          # Etapa 2: extração do QuestDB (extrair, processar, deletar)
├── eda.py               # Etapa 3: EDA da tabela routers
├── eda_metrics.py       # Etapa 3: EDA da tabela device_metrics
├── conclusoes_eda.md   # Etapa 3: conclusões da EDA
├── features.py          # Etapa 4: engenharia de features (múltiplos dias)
├── modelo_ia.py         # Etapa 5: modelagem (regra + K-Means) [gerado por IA]
├── modelo.py            # (vazio, reservado)
├── data/
│   ├── raw/             # dados brutos (temporários, deletados após processar)
│   └── processed/       # features e classificações (pequenos, permanentes)
├── readme.md            # este arquivo
├── questdb.md           # documentação sobre QuestDB
├── material_estudo.md   # material teórico (ML, estatística, K-Means)
├── feedback.md          # feedback do professor
├── prompt.md            # prompt para IAs (modo professor)
├── explicacao_modelo_ia.md  # explicação detalhada do modelo_ia.py
└── historico_alteracoes.md  # histórico de alterações do projeto
```

## Como Funciona

1. **Coleta de dados (`extracao.py`):** extrai os dados do QuestDB dia a dia. Para cada dia, processa as features e deleta o dado bruto (Opção B — economiza disco).

2. **Análise exploratória (`eda.py`, `eda_metrics.py`):** explora os dados antes de modelar. Verifica dados faltantes, distribuições, outliers, tipos de colunas.

3. **Engenharia de features (`features.py`):** transforma os bytes acumulados em tráfego real por minuto (diff), agrupa por roteador e hora, calcula:
   - Tráfego comercial (8h-17h) e residencial (18h-7h)
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

A avaliação será feita verificando a localização de alguns roteadores, avaliando se é um endereço residencial ou comercial. Será usada a coluna `eh_fds` para comparar o comportamento em dias úteis vs fins de semana.
