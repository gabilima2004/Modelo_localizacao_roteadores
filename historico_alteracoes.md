# Histórico de Alterações do Projeto

> Este documento registra as principais alterações feitas no projeto,
> organizadas por data e etapa.

---

## 2026-07-27 — Início do projeto

### Etapa 1: Definição do Problema

- Criado `readme.md` com a visão geral do projeto
- Definido o objetivo: classificar roteadores como residencial/comercial
- Identificadas as fontes de dados: QuestDB (tabelas `routers` e `device_metrics`)
- Definido o critério de classificação: proporção de tráfego por período

### Etapa 2: Coleta de Dados

- Criado `extracao.py` para extrair dados do QuestDB
- Estratégia: `routers` tudo de uma vez, `device_metrics` dia a dia
- Funções: `conectar()`, `extrair_routers()`, `extrair_metrics_dia()`, `salvar()`, `ja_existe()`
- Configurações de conexão: host, porta 8812, user admin

### Documentação

- Criado `material_estudo.md` com teoria de ML, estatística e K-Means
- Criado `feedback.md` com feedback do professor
- Criado `questdb.md` com documentação sobre QuestDB (portas, single-database, autenticação)

---

## 2026-07-28 — Configuração do ambiente

### Configuração da VM Linux

- Configurado acesso SSH à VM (10.246.47.166) via VS Code Remote
- Gerada chave SSH e copiada para a VM
- Criado venv e instaladas dependências: `psycopg2-binary`, `pandas`, `pyarrow`, `scikit-learn`

### Descoberta do schema das tabelas

- Identificadas as colunas de `routers`: router_mac, timestamp, manufacturer, model, user_ppp, location, city, state, latitude, longitude
- Identificadas as colunas de `device_metrics`: device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down, last_connected
- Decisão: remover `last_connected` (100% nulo) e `manufacturer` (todos TP-Link)

---

## 2026-07-28 — Etapa 3: EDA

### EDA da tabela `routers` (`eda.py`)

- Descoberto: 12.177 linhas, mas só 6.012 roteadores únicos (duplicatas!)
- Descoberta: tabela `routers` é série temporal (tem timestamp), não estática
- Solução: deduplicação pegando a versão mais recente de cada roteador
- Adicionado `timestamp` e `user_ppp` na extração
- Descoberto: 66% dos roteadores sem localização
- Descoberto: 2 roteadores com latitude inválida (-227, erro de digitação)
- Descoberto: todos os roteadores são TP-Link, no RJ, concentrados em Nova Friburgo

### EDA da tabela `device_metrics` (`eda_metrics.py`)

- Descoberto: 15,8 milhões de linhas por dia (não 7,2M como esperado)
- Motivo: cada linha é um device, não um roteador (média 1,7 devices/roteador)
- Descoberta crítica: bytes_up e bytes_down são **acumulados**, não por minuto
- `last_connected`: 100% nulo, removido da extração
- Dados faltantes: muito poucos nas colunas principais (qualidade boa)

### Documentação

- Criado `conclusoes_eda.md` com todas as descobertas
- Atualizado `readme.md` com as descobertas da EDA
- Definida estratégia de sazonalidade: dias úteis vs fds, férias, Copa 2026

---

## 2026-07-29 — Etapa 4: Engenharia de Features

### Criação do `features.py`

- Função `calcular_deltas()`: calcula diff() por device_mac, trata reinícios (delta < 0)
- Função `trafego_por_hora()`: agrupa por roteador + hora e soma
- Função `trafego_comercial()`: filtra horas 8-17 e soma por roteador
- Função `trafego_residencial()`: filtra horas 18-7 e soma por roteador
- Função `razao_comercial()`: calcula proporção comercial/(comercial+residencial)
- Função `hora_pico()`: usa idxmax() para achar a hora de maior tráfego
- Função `perfil_horario()`: pivot_table para criar 24 colunas (h_0 a h_23)
- Função `main()`: orquestra tudo e salva em CSV

### Resultados

- 3.349 roteadores após filtro (removidos 122 com 20+ horas zeradas)
- 30 features por roteador
- Arquivo salvo em `data/processed/features_2026-04-01.csv`

### Organização de pastas

- Criada estrutura `data/raw/` (dados brutos) e `data/processed/` (features)
- Atualizados `extracao.py`, `eda.py`, `eda_metrics.py`, `features.py` para usar novas pastas
- Criado `.gitignore` para não subir arquivos grandes

---

## 2026-07-29 — Etapa 5: Modelagem

### Criação do `modelo_ia.py` (gerado por IA)

- Função `classificar_regra()`: regra de negócio (razao > 0.5 → comercial)
- Função `classificar_kmeans()`: K-Means com normalização L1
- Função `interpretar_grupos()`: descobre qual grupo é comercial/residencial
- Função `comparar_metodos()`: compara regra vs K-Means (matriz de confusão)
- Função `analisar_perfil_grupos()`: mostra perfil horário médio de cada grupo

### Problema 1: Outlier por volume

- K-Means agrupou 1 roteador sozinho (tráfego 449x a mediana)
- Solução inicial: remover outliers com tráfego > 100x a mediana
- Resultado: 2 outliers removidos, 3.347 roteadores restantes

### Problema 2: K-Means agrupando por volume, não por padrão

- Com StandardScaler, grupos separavam "muito tráfego" vs "pouco tráfego"
- Razões comerciais médias eram quase iguais (0.358 vs 0.353)
- Solução: trocar StandardScaler por normalização L1 (dividir cada perfil pela soma)
- Resultado: grupos agora separam por padrão (0.232 vs 0.461), concordância 63.9%

### Documentação

- Criado `explicacao_modelo_ia.md` com explicação detalhada do código
- Criado `prompt.md` com prompt para IAs (modo professor)

---

## 2026-08-03 — Refinamentos

### Mudança na detecção de outliers

- Removida detecção por volume (mediana × 100)
- Nova detecção: padrão plano (std baixo do perfil normalizado)
- Outliers agora classificados como `padrao_anomalo` (não removidos)
- Motivo: depois da normalização L1, o volume não existe mais; o problema é o padrão

### Processamento de múltiplos dias (`features.py`)

- `features.py` agora processa todos os arquivos `metrics_*.csv` da pasta `data/raw/`
- Adicionadas colunas: `data`, `dia_semana` (0=seg, 6=dom), `eh_fds` (True/False)
- Funções agora recebem `df_metrics` como parâmetro (não usam variável global)
- Resultado consolidado em `features_todos_dias.csv`
- Permite analisar dias úteis vs fins de semana separadamente

### Opção B: extrair e deletar (`extracao.py`)

- Adicionada flag `DELETAR_APOS_PROCESSAR = True`
- Após extrair cada dia, processa as features e deleta o CSV bruto
- Motivo: 4 meses de CSV seriam ~180GB; features são ~120MB
- No final, consolida todas as features em um único arquivo

### Atualizações de documentação

- Atualizado `readme.md` com estrutura do projeto, metodologia e estratégia
- Criado `historico_alteracoes.md` (este arquivo)

---

## 2026-08-03 a 2026-08-04 — Etapa 5 (refinamentos), Etapa 6 e visualizações

### Etapa 5: Modelagem — refinamentos

- **Detecção de outliers**: alterada de volume (mediana × 100) para padrão plano (std do perfil normalizado). Outliers agora classificados como `padrao_anomalo` (não removidos)
- **Agregação de múltiplos dias**: implementada separação em 2 perfis por roteador (dias úteis vs fins de semana). O K-Means agora vê 48 colunas (24 horas × 2 períodos)
- **Normalização L1**: mantida (divide cada perfil pela soma, comparando forma não volume)
- **Resultados com 1 mês de dados**:
  - 3.932 roteadores classificados
  - Silhouette Score: 0.3935
  - Concordância regra vs K-Means: 90.8%
  - Grupo comercial: pico às 18h (úteis), queda no fds
  - Grupo residencial: pico às 23h, sobe no fds

### Etapa 4: Features — correções e melhorias

- **Feriados**: adicionada biblioteca `holidays` no `features.py` para tratar feriados como "não útil" (junto com sábados e domingos)
- **Múltiplos dias**: `features.py` agora processa todos os arquivos `metrics_*.csv` da pasta `data/raw/` e consolida em `features_todos_dias.csv`
- **Correção do perfil horário**: adicionado `reindex` para garantir 24 colunas mesmo em dias com poucas horas de dados
- **Dia da semana**: adicionadas colunas `data`, `dia_semana` (0=seg, 6=dom) e `eh_fds`

### Etapa 2: Coleta — Opção B (extrair e deletar)

- Implementada flag `DELETAR_APOS_PROCESSAR = True` no `extracao.py`
- Após extrair cada dia, processa as features e deleta o CSV bruto (economia de disco)
- Corrigida verificação de "já processado": agora verifica `data/processed/features_*.csv` (resultado) em vez de `data/raw/` (que foi deletado)

### Etapa 6: Avaliação

- Criado `avaliacao_ia.py` com 6 funções de validação:
  - Juntar classificação com localização (inner join)
  - Amostra manual (olhar endereços)
  - Distribuição por cidade
  - Estatísticas por cidade
  - Concordância por cidade
  - Mapa HTML com folium (roteadores coloridos no mapa)
- **Resultados da avaliação**:
  - 100% dos roteadores classificados têm localização
  - Amostra manual confirmou: "Casa" = residencial, "Galpão/Centro" = comercial
  - Cidades pequenas (Cordeiro, Quissamã) têm 0% comercial
  - Cidades turísticas (Búzios) têm mais comercial (12.3%)
  - Concordância por cidade: 83.8% a 100%

### Visualizações

- Criado `graficos_ia.py` com 9 gráficos PNG:
  1. Distribuição pela regra (pizza)
  2. Distribuição pelo K-Means (pizza)
  3. Concordância regra vs K-Means (barras)
  4. Perfil horário comparativo (comercial vs residencial, úteis vs fds)
  5. Volume médio por hora (barras agrupadas)
  6. Volume total (boxplot)
  7. Comercial vs residencial por cidade (barras empilhadas)
  8. Histograma da razão comercial
  9. Scatter razão comercial vs hora de pico
- Corrigido erro do `boxplot` (parâmetro `labels` → `tick_labels` no matplotlib recente)

### Documentação

- Criado `explicacao_modelo_ia.md` com explicação detalhada do código
- Atualizado `readme.md` com a estrutura final do projeto

---

## Próximos passos

- [x] Etapa 7: Interpretação & Deploy — relatório final e pipeline automatizado criados
- [ ] Re-processar com feriados (apagar features dos dias de feriado e rodar de novo)
- [ ] Testar K=3 no K-Means (para encontrar grupo "misto")
- [ ] Considerar férias escolares e Copa do Mundo 2026 na análise
- [ ] Investigar roteadores comerciais com pico de madrugada (padarias, farmácias 24h)
- [ ] Ampliar para 4 meses de dados (sazonalidade completa)
- [ ] Preencher localização dos 66% de roteadores sem endereço
