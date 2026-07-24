# Feedback do Professor — Etapas do Projeto

> Este documento registra o feedback crítico e detalhado de cada etapa do projeto,
> para servir de referência durante o desenvolvimento.

---

# Etapa 1: Definição do Problema — Feedback

## Avaliação geral: ✅ Bom ponto de partida, mas precisa de refinamento

O readme descreve corretamente **o que** será feito tecnicamente, mas falta
completude para ser uma definição de problema robusta.

## Pontos positivos

- ✅ Objetivo claro: classificar roteadores em residencial/comercial
- ✅ Fontes de dados identificadas (QuestDB, duas tabelas: `routers` e `device_metrics`)
- ✅ Critério de classificação definido (proporção de tráfego por período)
- ✅ Fluxo de funcionamento descrito em 4 passos

## Pontos a melhorar

### 1. Falta a "pergunta de negócio"

O readme diz *o que* você vai fazer tecnicamente, mas não diz *por que*.
Perguntas que você deve se fazer e adicionar ao readme:

- Para que serve essa classificação? Quem vai usar o resultado?
- Qual decisão será tomada com essa informação?
  - Planejar capacidade da rede?
  - Cobrança diferente por perfil?
  - Segmentação de clientes?
  - Detecção de anomalias?

> **Por que importa:** sem o "por quê", você corre o risco de otimizar a
> métrica errada. A pergunta de negócio guia quais features importam e
> qual nível de precisão é aceitável.

### 2. "Maior parte do tráfego" é vago

"Maior parte" significa >50%? >60%? Esse limiar precisa ser definido —
ou melhor, **descoberto** na análise.

O readme já pressupõe a regra (`> 50%`), mas a EDA pode revelar que:
- O limiar ideal é 0.43, não 0.5
- Uma única regra não captura roteadores de uso misto
- O critério precisa de mais de uma variável

> **Sugestão:** reformular para "a proporção será determinada durante a
> análise exploratória" em vez de fixar um número agora.

### 3. Falta definir o critério de sucesso

Como você vai saber se a classificação está correta? Opções a documentar:

- Validar manualmente uma amostra (olhar endereços no mapa)
- Cruzar com a localização (tabela `routers`) — zonas comerciais vs residenciais
- Comparar regra vs clustering (se concordarem, ganha confiança)

> **Por que importa:** sem critério de sucesso, você não sabe se "terminou".
> Precisa de uma definição objetiva de "bom o suficiente".

### 4. O período residencial inclui madrugada

O readme diz "18h às 8h", mas as pessoas dormem de 0h-6h. O readme não
menciona essa nuance. Isso será tratado na engenharia de features, mas
vale registrar como uma limitação/decisão:

- O período residencial "bruto" é 18h-8h (14 horas)
- Mas dentro dele há sub-períodos com comportamentos diferentes:
  - 18h-23h: pico de uso (Netflix, YouTube)
  - 23h-6h: baixo tráfego (dormindo)
  - 6h-8h: tráfego matinal (acordando)

> **Sugestão:** adicionar uma nota no readme sobre essa nuance e que ela
> será tratada com perfil horário (24 valores) na Etapa 4.

### 5. Faltam detalhes sobre os dados

O readme não menciona informações críticas que afetam todas as decisões
técnicas:

| Informação | Valor (a preencher) |
|---|---|
| Granularidade dos dados | A cada 1 minuto |
| Período histórico | Desde abril (~120 dias) |
| Número de roteadores | ~5000 |
| Volume estimado | ~864 milhões de linhas |
| Colunas de `routers` | ? (a descobrir) |
| Colunas de `device_metrics` | ? (a descobrir) |

> **Dica:** adicione uma seção "Dados" no readme com essas informações.
> Conhecer o volume e a granularidade é parte da definição do problema.

---

# Etapa 2: Coleta de Dados — Feedback

## Avaliação geral: ✅ Estratégia correta, execução bem planejada

A análise de volume e a estratégia de extração estão corretas e mostram
pensamento crítico sobre o problema.

## Análise de volume — correção

O cálculo original foi:

$$60 \times 24 \times 4 \times 5000 = 28.800.000 \text{ linhas}$$

Mas "4" aqui foi interpretado como 4 dias, quando na verdade são ~4 meses
(abril a julho = ~120 dias). O cálculo correto é:

$$5000 \times 60 \times 24 \times 120 \approx 864.000.000 \text{ linhas}$$

> **Conclusão se mantém:** é muito dado, precisa de extração em blocos.

## Estratégia: "routers tudo, device_metrics por dia"

**Avaliação: ✅ Correto e justificado**

### Tabela `routers` (~5000 linhas)
- É estática (não muda a cada minuto) ✅
- Volume pequeno → carrega tudo de uma vez ✅
- Não há necessidade de blocos ✅

### Tabela `device_metrics` (~864M linhas)
- Volume enorme → precisa de extração em blocos ✅
- Extrair por dia é uma boa granularidade ✅
- ~7,2 milhões de linhas/dia é gerenciável ✅

> **Justificativa do professor:** a granularidade diária é boa porque:
> 1. Cada arquivo tem tamanho razoável (~500MB-1GB em CSV)
> 2. Permite retomar a extração se interrompida (pula dias já baixados)
> 3. Permite processar dia a dia na Etapa 4 (engenharia de features)

## Formato de saída: CSV vs Parquet

| | CSV | Parquet |
|---|---|---|
| **Simples de entender** | ✅ Sim (texto puro, abre no Excel) | ❌ Binário (não abre no editor) |
| **Tamanho do arquivo** | ❌ Grande (~500MB-1GB/dia) | ✅ ~10x menor (~50-100MB/dia) |
| **Velocidade de leitura** | ❌ Lento | ✅ Muito rápido |
| **Preserva tipos** | ❌ Não (tudo vira texto) | ✅ Sim (int, float, datetime) |
| **Para 864M linhas** | ❈ Inviável a longo prazo | ✅ Viável |

> **Recomendação:** comece com CSV para **entender** o formato (abra o
> arquivo, veja as linhas). Mas para o projeto real com esse volume,
> **Parquet é essencial**. Você pode migrar depois.

## Estrutura do arquivo `extracao.py`

**Avaliação: ✅ Boa separação em funções**

A estrutura com funções separadas (`conectar`, `extrair_routers`,
`extrair_metrics_dia`, `salvar`, `main`) está correta porque:

- Cada função faz **uma coisa só** (princípio de responsabilidade única)
- Permite testar cada parte isoladamente
- Permite reutilizar `conectar()` em outros arquivos depois

## Melhoria sugerida: queries com `SELECT` específico

**Avaliação: ✅ Correto — o aluno identificou isso sozinho**

Em vez de `SELECT * FROM ...`, é melhor usar `SELECT coluna1, coluna2, ...`
porque:

1. **Menos dados transferidos pela rede** — se a tabela tem 20 colunas e
   você precisa de 4, trazendo `*` transfere 5x mais dados
2. **Menos memória usada** — o DataFrame fica menor
3. **Menos espaço em disco** — o CSV/Parquet fica menor
4. **Código mais explícito** — quem lê o código sabe exatamente o que
   está sendo usado

> **Bloqueador:** para escrever as queries específicas, é preciso saber
> o schema real das tabelas. O aluno precisa rodar queries de descoberta:
>
> ```sql
> SELECT * FROM routers LIMIT 1;
> SELECT * FROM device_metrics LIMIT 1;
> ```

## Pontos a verificar antes de executar

1. **Schema das tabelas:** quais colunas existem em cada tabela?
   Necessário para queries específicas e para a Etapa 4.

2. **Coluna de identificação:** qual coluna identifica o roteador em
   `device_metrics`? É `router_id`? `device_id`? É a coluna que conecta
   as duas tabelas — crucial para todo o projeto.

3. **Granularidade:** confirmar se os dados vêm a cada 1 minuto.
   Isso afeta o cálculo de deltas na Etapa 4.

4. **Configurações de conexão:** host, porta, usuário e senha do QuestDB
   precisam ser ajustados no topo do arquivo.

5. **Dependências:** instalar `psycopg2-binary`, `pandas`, e `pyarrow`
   (se usar Parquet).

---

# Próximos passos sugeridos

1. Descobrir o schema das tabelas (rodar `SELECT ... LIMIT 1`)
2. Reescrever as queries com colunas específicas
3. Testar a conexão com o QuestDB
4. Extrair um único dia para validar o pipeline
5. Se funcionar, executar a extração completa
6. Avançar para a Etapa 3 (EDA) com os dados extraídos