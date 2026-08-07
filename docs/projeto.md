# Documentação Técnica do Projeto

> Manual do desenvolvedor: detalhes técnicos, EDA, explicação do código e histórico.

---

# 1. Visão Geral do Projeto

## Objetivo

Classificar roteadores de internet como **residenciais** ou **comerciais** baseado no padrão de tráfego de dados ao longo do tempo.

## Status do projeto

| Etapa                     | Status       | Arquivo principal                         |
| ------------------------- | ------------ | ----------------------------------------- |
| 1. Definição do Problema  | ✅ Concluída | `readme.md`                               |
| 2. Coleta de Dados        | ✅ Concluída | `extracao.py`                             |
| 3. EDA                    | ✅ Concluída | `eda.py`, `eda_metrics.py`                |
| 4. Engenharia de Features | ✅ Concluída | `features.py`                             |
| 5. Modelagem              | ✅ Concluída | `modelo_ia.py`                            |
| 6. Avaliação              | ✅ Concluída | `avaliacao_ia.py`, `graficos_ia.py`       |
| 7. Interpretação & Deploy | ✅ Concluída | `relatorio_final_ia.md`, `pipeline_ia.py` |

## Estrutura de arquivos

```
Modelo_localizacao_roteadores/
├── extracao.py                    # Etapa 2: extração do QuestDB
├── eda.py                         # Etapa 3: EDA da tabela routers
├── eda_metrics.py                 # Etapa 3: EDA da tabela device_metrics
├── features.py                    # Etapa 4: engenharia de features
├── modelo_ia.py                   # Etapa 5: modelagem (regra + K-Means)
├── modelo_hdbscan_ia.py           # Etapa 5: modelagem alternativa (HDBSCAN)
├── avaliacao_ia.py                # Etapa 6: avaliação com localização
├── graficos_ia.py                 # Etapa 6: geração de gráficos
├── comparacao_humana_ia.py        # Etapa 6: comparação com análise humana (Grafana)
├── validacao_manual_ia.py         # Etapa 6: validação manual (20 endereços)
├── analise_volume_sazonalidade_ia.py  # Etapa 6: análise de volume e sazonalidade
├── teste_normalizacao_ia.py       # Etapa 6: teste de normalizações
├── pipeline_ia.py                 # Etapa 7: pipeline automatizado
├── data/
│   ├── raw/                       # dados brutos (temporários)
│   └── processed/                 # features e classificações
│       └── graficos/              # gráficos PNG
├── graficos/                      # cópia dos gráficos PNG
├── docs/                          # documentação
│   ├── projeto.md                 # este arquivo
│   ├── referencia.md              # teoria e referências
│   └── prompt.md                  # prompt para IAs
├── readme.md                      # visão geral do projeto
└── relatorio_final_ia.md          # relatório final de insights
```

---

# 2. EDA (Análise Exploratória de Dados)

## EDA da tabela `routers` (`eda.py`)

Descobertas principais:

- 12.177 linhas, mas só 6.012 roteadores únicos (duplicatas)
- Tabela é série temporal (tem timestamp), não estática
- Solução: deduplicação pegando a versão mais recente com endereço
- 66% dos roteadores sem localização (antes da correção)
- 2 roteadores com latitude inválida (-227, erro de digitação)
- Todos TP-Link, no RJ, concentrados em Nova Friburgo

## EDA da tabela `device_metrics` (`eda_metrics.py`)

Descobertas principais:

- 15,8 milhões de linhas
- Cada linha é um device (média 1,7 devices/roteador)
- Bytes_up e bytes_down são acumulados
- `last_connected`: 100% nulo, removido
- Dados faltantes: muito poucos nas colunas principais

## Conclusões da EDA

- **Roteadores:** 6.016 únicos (tabela `routers` é série temporal, deduplicada por timestamp mais recente)
- **Fabricante:** todos TP-Link (variável constante, sem valor para o modelo)
- **Localização:** todos no RJ, concentrados em Nova Friburgo e região dos lagos
- **Dados faltantes:** 66% dos roteadores sem localização (validação será com os 34% que têm)
- **Latitude inválida:** 2 roteadores com latitude impossível (-227, provável erro de digitação)
- **Bytes acumulados:** `bytes_up` e `bytes_down` são contadores acumulados, não tráfego por minuto
- **`last_connected`:** 100% nulo, removido da extração
- **Sazonalidade:** considerar dias úteis vs fins de semana, férias escolares (jun/jul) e Copa do Mundo 2026

---

# 3. Detalhamento por etapa

## Etapa 2: Coleta de Dados (`extracao.py`)

Extrai dados do QuestDB dia a dia. Usa a "Opção B": extrair, processar features, deletar dado bruto (economiza disco). Deduplica a tabela `routers` priorizando linhas com endereço.

**Detalhes técnicos**: ver `docs/referencia.md` (portas, single-database, autenticação)

## Etapa 4: Engenharia de Features (`features.py`)

Transforma bytes acumulados em tráfego real por minuto (diff), agrupa por roteador e hora, calcula:

- Tráfego comercial (8h-18h) e residencial (18h-8h) — **só em dias úteis**
- Razão comercial (proporção do tráfego em horário comercial)
- Hora de pico
- Perfil horário (24 valores: h_0 a h_23)
- Dia da semana, flag de fim de semana, flag de feriado, mês

**Processa múltiplos dias** e consolida em `features_todos_dias.csv`.

## Etapa 5: Modelagem (`modelo_ia.py`)

Aplica duas abordagens:

1. **Regra de negócio**: razao_comercial > 0.5 → comercial
2. **K-Means**: agrupa por similaridade do perfil horário (48 colunas: úteis + fds)

**Detecção de outliers**: padrão plano (std baixo do perfil normalizado)

**Votação por mês**: Para lidar com a sazonalidade, o K-Means é rodado para cada mês separadamente. A classificação final é a que teve mais votos (moda).

## Etapa 5 (alternativa): HDBSCAN (`modelo_hdbscan_ia.py`)

Testamos o HDBSCAN como alternativa ao K-Means. Diferenças:

- **Não precisa K** — descobre o número de grupos sozinho
- **Outliers automáticos** — marca como -1 (ruído)
- **Grupos de qualquer forma** — não só circulares

**Configuração usada**: PCA 3D (37.8% variância) + `min_cluster_size=50` + `min_samples=5`

**Resultado**: 2 grupos encontrados, mas muito conservador:

- Grupo 0 (comercial): 76 roteadores (vs 453 do K-Means)
- Grupo 1 (residencial): 4.948 roteadores
- Ruído: 626 roteadores (11%)
- Concordância com regra: 82.1% (vs 91.9% do K-Means)

**Conclusão**: O HDBSCAN agrupou corretamente por padrão (horário do pico), não por volume. Mas é muito conservador para este problema. O K-Means é o melhor algoritmo porque sabemos que existem 2 grupos e precisamos classificar todos os roteadores.

## Etapa 6: Avaliação (`avaliacao_ia.py`, `graficos_ia.py`, `comparacao_humana_ia.py`, `validacao_manual_ia.py`)

Valida as classificações de três formas:

1. **Validação humana (Grafana)**: 4 roteadores analisados visualmente no Grafana. Resultado: 100% de acerto.
2. **Validação manual (endereços)**: 20 roteadores analisados olhando o endereço no Google Maps. O script `validacao_manual_ia.py` compara com o modelo. Indicadores: "CASA"/"Ap." = residencial, "LOJA"/"sala" = comercial.
3. **Comparação regra vs K-Means**: 91.9% de concordância.

Gera gráficos PNG em `data/processed/graficos/`:

- `04_perfil_horario_comparativo.png` — perfil horário: comercial vs residencial, úteis vs fds (mais importante)
- `06_volume_boxplot.png` — distribuição de volume total por grupo
- `08_por_cidade.png` — comercial vs residencial por cidade
- E outros (distribuição, concordância, histograma, scatter)

Também gera mapa HTML com folium (localização dos roteadores).

## Etapa 7: Interpretação & Deploy (`relatorio_final_ia.md`, `pipeline_ia.py`)

- **Relatório final**: insights, limitações, recomendações
- **Pipeline automatizado**: roda todas as etapas em sequência

---

# 4. Explicação do modelo_ia.py

## Carregamento dos dados

```python
df = pd.read_csv("data/processed/features_todos_dias.csv", index_col="router_mac")
```

O `index_col="router_mac"` usa o MAC como índice para permitir joins posteriores.

## Agregação: votação por mês

O `features_todos_dias.csv` tem uma linha por roteador POR DIA. O K-Means precisa de 1 linha por roteador.

**Solução: Votação por mês.**

1. Para cada mês, agregamos os dias úteis e fds (2 perfis).
2. O K-Means classifica o roteador em cada mês separadamente.
3. A classificação final é a que teve mais votos (a moda).

Isso faz com que um mês atípico (férias) não consiga mudar a classificação final sozinho.

## Detecção de outliers (padrão plano)

```python
std_perfil = perfil_normalizado.std(axis=1)
threshold = std_perfil.quantile(0.01)
mascara_outlier = std_perfil < threshold
```

- **Std** = Desvio Padrão. Mede o quanto os valores variam.
- Perfil com pico (normal): valores variam muito → std alto
- Perfil plano (anômalo): valores são iguais → std baixo
- O 1º percentil é o valor abaixo do qual estão apenas 1% dos roteadores.

## Regra de negócio

```python
classificacao = df["razao_comercial"].apply(
    lambda r: "comercial" if r > 0.5 else "residencial"
)
```

- `apply(lambda)`: aplica uma função a cada valor
- Se razão > 0.5 → comercial, senão → residencial

## K-Means

```python
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
grupos = kmeans.fit_predict(perfil_normalizado)
```

- `n_clusters=2`: número de grupos (comercial vs residencial)
- `random_state=42`: semente aleatória (resultado reproduzível)
- `n_init=10`: roda 10 vezes com centroides diferentes (evita mínimo local)
- `fit_predict`: treina o modelo E retorna os grupos

## Normalização L1

```python
soma_por_router = perfil.sum(axis=1)
perfil_normalizado = perfil.div(soma_por_router, axis=0)
```

- Divide cada perfil pela sua soma total
- Cada roteador vira uma distribuição que soma 1
- Comparamos a "forma" do tráfego, não o tamanho

## Interpretação dos grupos

```python
razao_por_grupo = df_com_grupos.groupby("grupo_kmeans")["razao_comercial"].mean()
grupo_comercial = razao_por_grupo.idxmax()
```

- O K-Means retorna grupos 0 e 1, mas não diz qual é qual
- O grupo com maior razao_comercial média → comercial
- `idxmax()`: retorna o ÍNDICE (nome do grupo) com o maior valor

## Comparação (matriz de confusão)

```python
matriz = pd.crosstab(comparacao["regra"], comparacao["kmeans"], margins=True)
```

- A diagonal principal são as **concordâncias**
- Fora da diagonal são as **discordâncias**

---

# 5. Histórico de Alterações

## 2026-07-27 — Início do projeto

### Etapa 1: Definição do Problema

- Criado `readme.md` com a visão geral do projeto
- Definido o objetivo: classificar roteadores como residencial/comercial
- Identificadas as fontes de dados: QuestDB (tabelas `routers` e `device_metrics`)
- Definido o critério de classificação: proporção de tráfego por período

### Etapa 2: Coleta de Dados

- Criado `extracao.py` para extrair dados do QuestDB
- Estratégia: `routers` tudo de uma vez, `device_metrics` dia a dia

## 2026-07-28 — Configuração do ambiente

- Configurado acesso SSH à VM via VS Code Remote
- Criado venv e instaladas dependências
- Identificadas as colunas das tabelas

## 2026-07-28 — Etapa 3: EDA

- Descoberto: 12.177 linhas, mas só 6.012 roteadores únicos (duplicatas!)
- Descoberta: tabela `routers` é série temporal (tem timestamp), não estática
- Descoberto: 66% dos roteadores sem localização
- Descoberta crítica: bytes_up e bytes_down são **acumulados**, não por minuto

## 2026-07-29 — Etapa 4: Engenharia de Features

- Criado `features.py` com cálculo de deltas, tráfego por hora, razão comercial
- Resultados: 3.349 roteadores após filtro, 30 features por roteador

## 2026-07-29 — Etapa 5: Modelagem

- Criado `modelo_ia.py` com regra de negócio e K-Means
- Problema 1: Outlier por volume → solução: remover outliers
- Problema 2: K-Means agrupando por volume → solução: normalização L1

## 2026-08-03 a 2026-08-04 — Refinamentos

- Detecção de outliers alterada para padrão plano (std do perfil normalizado)
- Implementada separação em 2 perfis (dias úteis vs fins de semana)
- Implementada Opção B (extrair, processar, deletar) no `extracao.py`
- Adicionados feriados no `features.py`
- Razão comercial agora calculada só em dias úteis

## 2026-08-05 — Rodada completa e validação humana

- Pipeline completo: 111 dias processados, 5.650 roteadores classificados
- Silhouette Score: 0.4711, Concordância: 91.8%
- Validação humana: 100% de acerto (4/4 roteadores analisados no Grafana)

## 2026-08-06 — Melhorias finais

- **Prioridade 2 (Volume)**: Testadas normalizações L1, L2 e Z-Score. Mantida L1 (volume é uma feature real, não viés).
- **Prioridade 4 (Sazonalidade)**: Implementada votação por mês no K-Means. Concordância subiu para 91.9%.
- **Documentação**: Consolidada em 3 arquivos (`projeto.md`, `referencia.md`, `prompt.md`).

## 2026-08-07 — Validação manual e HDBSCAN

- **Prioridade 5 (HDBSCAN)**: Testado HDBSCAN como alternativa ao K-Means. Resultado: agrupou corretamente por padrão (não por volume), mas foi muito conservador (76 comerciais vs 453 do K-Means, 626 ruído). Conclusão: K-Means é o melhor algoritmo para este problema.
- **Prioridade 1 (Ground truth)**: Criado `validacao_manual_ia.py` com 20 roteadores analisados manualmente (endereços no Google Maps). 10 com alta razão comercial, 10 com baixa. Indicadores: "CASA"/"Ap." = residencial, "LOJA"/"sala" = comercial.
- **Documentação atualizada**: `relatorio_final_ia.md` com seção detalhada do gráfico de perfil horário, seção do HDBSCAN, explicação do boxplot de volume e validação manual. `readme.md` e `docs/projeto.md` atualizados com a estrutura completa.
