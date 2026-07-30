# Conclusões da Etapa 3 — EDA (Análise Exploratória de Dados)

> Este documento resume todas as descobertas da análise exploratória,
> servindo de base para a Etapa 4 (Engenharia de Features).

---

# 1. Tabela `routers`

## 1.1 Visão geral

| Métrica                          | Valor                                  |
| -------------------------------- | -------------------------------------- |
| Total de linhas (com duplicatas) | 12.177                                 |
| Total de roteadores únicos       | 6.016                                  |
| Colunas                          | 10 (após incluir timestamp e user_ppp) |

### Descoberta: a tabela NÃO é estática

A tabela `routers` é uma **série temporal** — cada roteador tem múltiplas
linhas com timestamps diferentes. A localização e o `user_ppp` mudam ao
longo do tempo (roteadores são transferidos de endereço).

**Solução aplicada:** deduplicação pegando a versão mais recente de cada
`router_mac`:

```python
df.sort_values("timestamp", ascending=False).drop_duplicates("router_mac", keep="first")
```

## 1.2 Tipos de dados

| Coluna         | Tipo       | Observação                                |
| -------------- | ---------- | ----------------------------------------- |
| `router_mac`   | str        | Identificador único do roteador           |
| `timestamp`    | datetime64 | Data da última atualização do cadastro    |
| `manufacturer` | str        | Sempre "TP-Link" — **variável constante** |
| `model`        | str        | Predomínio de XX530vV2 (90%)              |
| `user_ppp`     | str        | Usuário associado ao roteador             |
| `location`     | str        | Endereço (66% vazio)                      |
| `city`         | str        | Cidade (66% vazio)                        |
| `state`        | str        | Sempre "RJ" (quando preenchido)           |
| `latitude`     | float64    | Coordenada geográfica                     |
| `longitude`    | float64    | Coordenada geográfica                     |

## 1.3 Dados faltantes

| Coluna         | Nulos | %    | Impacto                            |
| -------------- | ----- | ---- | ---------------------------------- |
| `router_mac`   | 0     | 0%   | ✅ Sem problema                    |
| `timestamp`    | 0     | 0%   | ✅ Sem problema                    |
| `manufacturer` | 20    | 0,3% | ✅ Irrelevante (todos são TP-Link) |
| `model`        | 27    | 0,4% | ✅ Pouco impacto                   |
| `user_ppp`     | 43    | 0,7% | ✅ Pouco impacto                   |
| `location`     | 3.948 | 66%  | ⚠️ Problema para validação         |
| `city`         | 3.951 | 66%  | ⚠️ Problema para validação         |
| `state`        | 3.951 | 66%  | ⚠️ Problema para validação         |
| `latitude`     | 3.657 | 61%  | ⚠️ Problema para validação         |
| `longitude`    | 3.657 | 61%  | ⚠️ Problema para validação         |

### Impacto dos nulos

- **Para o modelo:** sem impacto. O modelo usa `device_metrics`, não a localização.
- **Para a validação (Etapa 6):** só 34% dos roteadores têm localização.
  A validação será feita com essa amostra reduzida.

## 1.4 Latitude inválida

| router_mac       | latitude | longitude | city |
| ---------------- | -------- | --------- | ---- |
| `0c:ef:15:69:98` | -227.282 | -41.985   | NaN  |
| `0c:ef:11:f8`    | -227.475 | -41.953   | NaN  |

- 2 roteadores com latitude impossível (fora do Brasil: < -33 ou > 5)
- Provável erro de digitação: "227" em vez de "22.7"
- Longitude está correta (dentro do RJ)
- Ambos sem cidade preenchida
- **Decisão:** remover ou corrigir (são só 2 de 6.016 — 0,03%)

## 1.5 Distribuições

### Fabricante

| Fabricante | Quantidade | %    |
| ---------- | ---------- | ---- |
| TP-Link    | 5.996      | 100% |

**Conclusão:** `manufacturer` é uma **variável constante** — não discrimina
nada. Pode ser removida do modelo.

### Modelo

| Modelo   | Quantidade | %     |
| -------- | ---------- | ----- |
| XX530vV2 | 5.399      | 90%   |
| XX530v   | 585        | 10%   |
| EX220    | 2          | <0,1% |
| EX220V2  | 2          | <0,1% |
| EX521    | 1          | <0,1% |

**Conclusão:** pouca variedade. Os modelos minoritários não são
estatisticamente relevantes.

### Estado

| Estado | Quantidade |
| ------ | ---------- |
| RJ     | 2.065      |

**Conclusão:** todos os roteadores estão no Rio de Janeiro.

### Cidade

| Cidade                | Quantidade |
| --------------------- | ---------- |
| Nova Friburgo         | 724        |
| Arraial do Cabo       | 430        |
| Armação dos Búzios    | 350        |
| Teresópolis           | 281        |
| Cabo Frio             | 139        |
| Araruama              | 39         |
| Rio das Ostras        | 36         |
| Niterói               | 22         |
| Cordeiro              | 16         |
| Casimiro de Abreu     | 8          |
| São Pedro da Aldeia   | 6          |
| Carapebus             | 5          |
| Quissamã              | 5          |
| Campos dos Goytacazes | 4          |

**Conclusão:** roteadores concentrados na região serrana e dos lagos do RJ.
Nova Friburgo e Teresópolis (serra) + Arraial do Cabo e Búzios (litoral)
são as principais cidades.

---

# 2. Tabela `device_metrics`

## 2.1 Visão geral

| Métrica                  | Valor                           |
| ------------------------ | ------------------------------- |
| Linhas (1 dia)           | 15.872.503                      |
| Colunas                  | 7 (após remover last_connected) |
| Tamanho do arquivo (CSV) | ~1,7 GB/dia                     |

### Por que mais linhas que o esperado?

Esperado: 6.012 roteadores × 1.440 minutos = ~8,7 milhões
Real: 15,8 milhões

**Motivo:** cada linha é um **device** conectado a um **router**.
Um roteador com 3 dispositivos gera 3 linhas por minuto.

**Média de devices por roteador:** 15.872.503 / (6.012 × 1.440) ≈ 1,7

## 2.2 Tipos de dados

| Coluna         | Tipo       | Observação                        |
| -------------- | ---------- | --------------------------------- |
| `device_mac`   | str        | Identificador do dispositivo      |
| `router_mac`   | str        | Identificador do roteador         |
| `timestamp`    | datetime64 | Momento da medição                |
| `bytes_up`     | float64    | **Acumulado** (não é por minuto!) |
| `bytes_down`   | float64    | **Acumulado** (não é por minuto!) |
| `packets_up`   | float64    | **Acumulado** (não é por minuto!) |
| `packets_down` | float64    | **Acumulado** (não é por minuto!) |

## 2.3 Dados faltantes

| Coluna           | Nulos      | %        | Impacto                         |
| ---------------- | ---------- | -------- | ------------------------------- |
| `device_mac`     | 0          | 0%       | ✅                              |
| `router_mac`     | 0          | 0%       | ✅                              |
| `timestamp`      | 0          | 0%       | ✅                              |
| `bytes_up`       | 80         | 0,0005%  | ✅ Irrelevante                  |
| `bytes_down`     | 11         | 0,00007% | ✅ Irrelevante                  |
| `packets_up`     | 8.351      | 0,05%    | ✅ Irrelevante                  |
| `packets_down`   | 93         | 0,0006%  | ✅ Irrelevante                  |
| `last_connected` | 15.872.503 | 100%     | ❌ **Coluna inútil — removida** |

**Conclusão:** qualidade dos dados é excelente nas colunas principais.

## 2.4 Estatísticas descritivas

### bytes_up (ACUMULADO — não é tráfego por minuto)

| Estatística | Valor           | Em GB     |
| ----------- | --------------- | --------- |
| count       | 15.872.423      | —         |
| mean        | 4.513.833.000   | 4,5 GB    |
| std         | 20.255.770.000  | 20,3 GB   |
| min         | 0               | 0         |
| 25%         | 8.616.801       | 0,0086 GB |
| 50%         | 216.323.400     | 0,22 GB   |
| 75%         | 1.600.229.000   | 1,6 GB    |
| max         | 637.146.300.000 | 637 GB    |

### bytes_down (ACUMULADO)

| Estatística | Valor           | Em GB     |
| ----------- | --------------- | --------- |
| count       | 15.872.492      | —         |
| mean        | 591.757.400     | 0,59 GB   |
| std         | 6.426.773.000   | 6,4 GB    |
| min         | 0               | 0         |
| 25%         | 5.873.280       | 0,0059 GB |
| 50%         | 35.030.320      | 0,035 GB  |
| 75%         | 146.959.500     | 0,15 GB   |
| max         | 350.517.600.000 | 350 GB    |

### 🚨 Descoberta crítica: bytes são acumulados!

Os valores de `bytes_up` e `bytes_down` são **contadores acumulados**
(cumulative counters). O roteador soma o tráfego desde que foi ligado.

**Exemplo:**

```
timestamp           bytes_up (acumulado)
14:00               1.000.000    ← 1 MB total desde que ligou
14:01               1.050.000    ← 1,05 MB total
14:02               1.120.000    ← 1,12 MB total
```

O tráfego **real** de cada minuto é a **diferença** (delta):

```
14:00 → 14:01:  1.050.000 - 1.000.000 = 50.000 bytes (50 KB)
14:01 → 14:02:  1.120.000 - 1.050.000 = 70.000 bytes (70 KB)
```

**Impacto:** a Etapa 4 (Engenharia de Features) precisa calcular os
deltas antes de qualquer análise de tráfego.

### Problema do contador que zera

Quando o roteador reinicia, o contador volta a zero:

```
14:00    bytes_up = 1.000.000
14:01    bytes_up = 0            ← reiniciou! delta = -1.000.000
14:02    bytes_up = 30.000       ← delta = 30.000
```

**Solução:** quando delta for negativo, tratar como reinício do contador
(ignorar ou usar o próprio valor como tráfego real).

## 2.5 Devices por roteador

- 3.538 roteadores têm pelo menos 1 device conectado
- 2.478 roteadores não têm nenhum device conectado nesse dia
- Média: ~1,7 devices por roteador

**Pergunta em aberto:** roteadores sem devices devem entrar no modelo?

---

# 3. Estimativas de volume

## 3.1 Por dia

| Métrica                | Valor         |
| ---------------------- | ------------- |
| Linhas por dia         | ~15,8 milhões |
| Tamanho CSV por dia    | ~1,7 GB       |
| RAM necessária por dia | ~2-3 GB       |

## 3.2 Por período completo (120 dias)

| Métrica                          | Valor                   |
| -------------------------------- | ----------------------- |
| Linhas totais                    | ~1,9 bilhões            |
| Tamanho CSV total                | ~205 GB                 |
| RAM necessária (tudo de uma vez) | ~240-360 GB ❌ inviável |

## 3.3 Estratégia: processamento incremental

Processar **dia a dia** e acumular só o **resultado** (não os dados brutos):

| Etapa                                     | Linhas       | RAM        |
| ----------------------------------------- | ------------ | ---------- |
| Dados brutos de 1 dia                     | 15,8 milhões | ~2-3 GB    |
| Resultado de 1 dia (1 linha por roteador) | ~6.000       | ~1 MB      |
| Resultado de 120 dias                     | ~720.000     | ~100 MB ✅ |

---

# 4. Sazonalidade — consideração importante

O comportamento da rede varia conforme o período:

| Período              | Comportamento esperado                 |
| -------------------- | -------------------------------------- |
| Dias úteis           | Pico comercial 8h-18h                  |
| Fins de semana       | Tráfego espalhado o dia todo           |
| Férias escolares     | Mais tráfego residencial durante o dia |
| Copa do Mundo (2026) | Picos em horários de jogo              |
| Feriados             | Parecido com fim de semana             |

**Risco:** um roteador residencial durante as férias pode parecer comercial
(crianças em casa usando internet das 8h-18h).

## 4.1 Estratégia adotada

**Abordagem:** usar todos os dados, mas **agrupar por tipo de dia**.

### Separação por prioridade:

| Prioridade            | O que separar                | Dificuldade | Como                               |
| --------------------- | ---------------------------- | ----------- | ---------------------------------- |
| 1ª (fazer primeiro)   | Dias úteis vs fins de semana | Fácil       | `dt.dayofweek` (0-4 útil, 5-6 fds) |
| 2ª (refinar depois)   | Feriados nacionais/estaduais | Média       | Biblioteca `holidays` do Python    |
| 3ª (investigar)       | Férias escolares (jun/jul)   | Média       | Marcar período manualmente         |
| 4ª (atenção especial) | Dias de jogo da Copa 2026    | Manual      | Pesquisar datas e marcar           |

## 4.2 Atenção especial: Copa do Mundo 2026

Como todos os dados são de 2026, a Copa é um **evento de confusão**
(confounding event). Nos dias de jogo do Brasil:

- Empresas pararam → tráfego comercial caiu em horário normal
- Pessoas assistiram em casa → tráfego residencial subiu

**Risco:** sem separar esses dias, roteadores comerciais podem parecer
residenciais (tráfego baixo das 14h-18h) e vice-versa.

**Ação:** pesquisar as datas dos jogos do Brasil na Copa 2026 e marcar
esses dias como anômalos para análise separada.

## 4.3 Feriados regionais

Feriados regionais (municipais) são difíceis de identificar
automaticamente. Estratégia:

1. Começar com feriados **nacionais** (biblioteca `holidays`)
2. Adicionar feriados **estaduais** do RJ
3. Feriados **municipais** — se necessário, marcar manualmente

**Risco:** um roteador comercial em dia de feriado parece residencial.

---

# 5. Resumo das decisões tomadas

| Decisão                                    | Motivo                                 |
| ------------------------------------------ | -------------------------------------- |
| Deduplicar `routers` por `router_mac`      | Tabela é série temporal, não estática  |
| Incluir `timestamp` em `routers`           | Necessário para deduplicação           |
| Remover `last_connected` da extração       | 100% nulo — inútil                     |
| `manufacturer` não é feature útil          | Todos são TP-Link (constante)          |
| Validar modelo com 34% que tem localização | 66% sem localização                    |
| Processar `device_metrics` dia a dia       | Volume muito grande para carregar tudo |
| Calcular deltas na Etapa 4                 | Bytes são acumulados, não por minuto   |
| Considerar sazonalidade                    | Férias/finais de semana alteram padrão |

---

# 6. Próximos passos (Etapa 4 — Engenharia de Features)

1. **Calcular deltas** de bytes_up, bytes_down, packets_up, packets_down
   - Agrupar por `device_mac`, ordenar por `timestamp`, aplicar `.diff()`
   - Tratar deltas negativos (reinício do contador)

2. **Extrair hora do dia** do timestamp
   - `df["timestamp"].dt.hour` → 0 a 23

3. **Classificar período** (comercial vs residencial)
   - 8h-18h → comercial
   - 18h-8h → residencial

4. **Identificar dia da semana**
   - `df["timestamp"].dt.dayofweek` → 0 (segunda) a 6 (domingo)
   - Separar dias úteis de fins de semana

5. **Agrupar por roteador** e calcular features:
   - Tráfego total comercial
   - Tráfego total residencial
   - Razão comercial / total
   - Hora de pico
   - Perfil horário (24 valores: tráfego por hora 0-23)

6. **Salvar resultado** em arquivo (1 linha por roteador)
