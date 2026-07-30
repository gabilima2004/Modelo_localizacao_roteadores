# Modelo Residencial Comercial

## Visão Geral

Este projeto é um modelo de classificação de roteadores em um banco de dados **QuestDB**. O modelo classifica os roteadores como **residenciais** ou **comerciais** com base no padrão de tráfego de dados ao longo do tempo.

## Metodologia

A classificação é baseada na análise do tráfego de dados por períodos do dia:

- **Período comercial:** das **8h às 18h**
- **Período residencial:** fora do horário comercial (das 18h às 8h)

### Critério de Classificação

- Os roteadores que apresentam a **maior parte do tráfego** dentro do período comercial (8h–18h) são classificados como **comerciais**.
- Os roteadores cujo tráfego é predominantemente fora do período comercial são classificados como **residenciais**.
- a proporção será determinada durante a análise exploratória

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

## Como Funciona

1. **Coleta de dados:** O tráfego de dados de cada roteador é registrado na tabela `device_metrics` com carimbo de data/hora.
2. **Análise por período:** O tráfego de cada roteador é agregado e comparado entre o período comercial (8h–18h) e o período residencial (18h–8h).
3. **Classificação:** Com base na proporção de tráfego em cada período, o roteador é classificado como comercial ou residencial.
4. **Enriquecimento:** A localização do roteador, disponível na tabela `routers`, pode ser utilizada para enriquecer a análise e validação dos resultados.

## Avaliação

A avaliação será feita verificando a localização de alguns roteadores, avaliando se é um endereço residencial ou comercial.
