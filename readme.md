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

## Fontes de Dados

Os dados estão armazenados no **QuestDB** e são distribuídos em duas tabelas principais:

| Tabela | Descrição |
|---|---|
| `routers` | Contém os dados de localização dos roteadores |
| `device_metrics` | Contém os dados de tráfego dos dispositivos |

## Como Funciona

1. **Coleta de dados:** O tráfego de dados de cada roteador é registrado na tabela `device_metrics` com carimbo de data/hora.
2. **Análise por período:** O tráfego de cada roteador é agregado e comparado entre o período comercial (8h–18h) e o período residencial (18h–8h).
3. **Classificação:** Com base na proporção de tráfego em cada período, o roteador é classificado como comercial ou residencial.
4. **Enriquecimento:** A localização do roteador, disponível na tabela `routers`, pode ser utilizada para enriquecer a análise e validação dos resultados.