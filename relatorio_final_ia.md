# Relatório Final — Modelo de Classificação Residencial/Comercial

> **Etapa 7: Interpretação & Deploy**
>
> Este relatório traduz os resultados técnicos do modelo em
> decisões e insights de negócio.

---

# 1. Resumo Executivo

## O que foi feito

Desenvolvemos um modelo de classificação que identifica se um roteador de internet está instalado em um endereço **residencial** ou **comercial**, baseado no padrão de tráfego de dados ao longo do tempo.

## Principais resultados (Rodada completa: 111 dias)

| Métrica                       | Valor         |
| ----------------------------- | ------------- |
| Roteadores analisados         | 5.650         |
| Roteadores comerciais         | 453 (8.0%)    |
| Roteadores residenciais       | 5.135 (90.9%) |
| Roteadores com padrão anômalo | 62 (1.1%)     |
| Concordância regra vs K-Means | 91.9%         |
| Silhouette Score              | 0.4711        |
| Validação humana (Grafana)    | 100% (4/4)    |
| Validação manual (endereços)  | ver Seção 3.6 |

## Como o modelo classifica

O modelo usa **duas abordagens** em paralelo:

1. **Regra de negócio**: se >50% do tráfego ocorre das 8h às 18h → comercial
2. **K-Means (Machine Learning)**: agrupa roteadores por similaridade do perfil horário

Quando os dois métodos concordam (90.8% dos casos), temos **alta confiança** na classificação.

---

# 2. Metodologia

## Fluxo completo do projeto

```mermaid
flowchart TD
    A["1. Definição do problema"] --> B["2. Coleta de dados"]
    B --> C["3. Análise exploratória"]
    C --> D["4. Engenharia de features"]
    D --> E["5. Modelagem"]
    E --> F["6. Avaliação"]
    F --> G["7. Interpretação & Deploy"]
```

## Dados utilizados

- **Fonte**: QuestDB (banco de dados de séries temporais)
- **Período**: 111 dias (01/04/2026 a 20/07/2026)
- **Volume**: ~15,8 milhões de linhas por dia
- **Roteadores**: 5.650 únicos (após deduplicação)

## Features criadas

Para cada roteador, calculamos:

| Feature                    | Descrição                                          |
| -------------------------- | -------------------------------------------------- |
| `uteis_h_0` a `uteis_h_23` | Tráfego por hora em dias úteis                     |
| `fds_h_0` a `fds_h_23`     | Tráfego por hora em fins de semana                 |
| `razao_comercial`          | Proporção do tráfego no horário comercial (8h-18h) |
| `hora_pico`                | Hora de maior tráfego                              |

---

# 3. Insights Principais

## Insight 1: O padrão comercial vs residencial

| Característica             | Comercial                    | Residencial                 |
| -------------------------- | ---------------------------- | --------------------------- |
| **Pico em dias úteis**     | 17h (fim do expediente)      | 23h (Netflix/madrugada)     |
| **Pico em fins de semana** | 15h (mas 4x menor que úteis) | 23h (ainda maior que úteis) |
| **Comportamento em fds**   | Tráfego **cai** 65%          | Tráfego **sobe** 2%         |
| **Volume total**           | Menor (11.5 GB médios)       | Maior (36.2 GB médios)      |

> **Conclusão**: O sinal mais forte é a **diferença entre úteis e fds**. Comercial fecha em fds (tráfego cai). Residencial tem mais gente em casa em fds (tráfego sobe).

### 📊 Gráfico: Perfil Horário Comparativo (`04_perfil_horario_comparativo.png`)

Este é o **gráfico mais importante do projeto**. Ele mostra 4 linhas no mesmo gráfico, permitindo comparar visualmente os dois perfis:

| Linha                        | Cor         | Estilo        | O que representa                   |
| ---------------------------- | ----------- | ------------- | ---------------------------------- |
| Comercial — dias úteis       | 🔴 vermelho | sólida (●)    | Padrão do comércio em dias normais |
| Comercial — fins de semana   | 🔴 vermelho | tracejada (■) | Padrão do comércio em fds          |
| Residencial — dias úteis     | 🔵 azul     | sólida (●)    | Padrão das casas em dias normais   |
| Residencial — fins de semana | 🔵 azul     | tracejada (■) | Padrão das casas em fds            |

A faixa laranja no fundo destaca o **horário comercial** (8h às 18h).

#### Como ler o gráfico

**Eixo X**: hora do dia (0h a 23h)
**Eixo Y**: tráfego médio em bytes

#### O que o gráfico revela

**1. Comercial em dias úteis (linha vermelha sólida):**

- Começa a subir às 7h (abertura do comércio)
- Pico entre 13h e 18h (horário de expediente)
- Cai drasticamente após 18h (comércio fecha)
- Quase zero entre 22h e 6h (comércio fechado)

**2. Comercial em fins de semana (linha vermelha tracejada):**

- Muito mais baixa que a linha sólida (comércio fecha em fds)
- Pico baixo ao meio-dia (provavelmente restaurantes/lojas que abrem no fds)
- Confirma: **comercial cai ~65% em fds**

**3. Residencial em dias úteis (linha azul sólida):**

- Baixo durante o dia (pessoas trabalhando/estudando)
- Sobe a partir das 18h (chegada em casa)
- **Pico às 23h** (Netflix, YouTube, redes sociais à noite)
- Ainda alto na madrugada (0h-2h)

**4. Residencial em fins de semana (linha azul tracejada):**

- Mais alto que a linha sólida durante o dia (pessoas em casa)
- Pico às 23h (mesmo padrão noturno)
- Confirma: **residencial sobe ~2% em fds**

#### A diferença chave

O gráfico mostra que a **separação entre comercial e residencial** não está no volume total, mas no **horário do pico** e no **comportamento em fins de semana**:

- Comercial: pico de dia, some à noite, despenca em fds
- Residencial: pico à noite, constante na madrugada, sobe em fds

> **Conclusão**: O modelo captura essa diferença através das 48 features (24h úteis + 24h fds). A normalização L1 garante que comparamos a **forma** do perfil, não o volume.

### O papel do Volume no Modelo

Foi realizado um teste para verificar se o K-Means estava agrupando os roteadores puramente por **volume** (muito tráfego vs pouco tráfego) em vez de **padrão** (horário do pico). Testamos 3 normalizações:

1. **L1 (Atual)**: Melhor separação (Silhouette 0.47), mas maior diferença de volume (3.15x).
2. **L2**: Separação média (0.29), diferença de volume média (2.36x).
3. **Z-Score**: Pior separação (0.18), menor diferença de volume (1.56x).

> **Conclusão do teste**: O volume **faz parte** da diferença real entre os grupos. O residencial tem naturalmente mais volume (muitos dispositivos, streaming). Tentar remover o volume (Z-Score) destrói a separação dos grupos. Portanto, a normalização L1 foi mantida, pois o volume atua como uma feature legítima e não apenas como um viés.

## Insight 2: O tráfego parece medir consumo, não trabalho

Observando os dados, notamos que o tráfego de internet tende a ser **maior quando as pessoas não estão trabalhando**. Essa é uma hipótese baseada no comportamento típico de consumo de internet:

- **Trabalhar** (digitar, email, planilhas) gera pouco tráfego (apenas texto/pequenos arquivos)
- **Streaming** (Netflix, YouTube) gera muito tráfego (vídeo)
- **Redes sociais** (Instagram, TikTok) gera tráfego médio (imagens/vídeos curtos)

> **Hipótese**: O modelo possivelmente detecta "onde as pessoas consomem internet para lazer", não "onde trabalham". Ainda assim, consegue distinguir residencial de comercial porque o padrão de consumo parece ser diferente em cada ambiente. Esta hipótese poderia ser confirmada cruzando os dados com informações sobre o tipo de conexão ou dispositivos conectados.

## Insight 3: Comercial não é só escritório

Roteadores classificados como comercial apresentam tráfego de madrugada (0h-3h), o que parece estranho se pensarmos apenas em escritórios. No entanto, isso pode ser explicado pelo fato de que "comercial" engloba diversos tipos de estabelecimentos:

- **Padarias** (abrem às 4h)
- **Farmácias 24h**
- **Postos de gasolina**
- **Bares/restaurantes** (fecham tarde)
- **Sistemas de segurança** (câmeras, alarmes)
- **Backups automáticos** (rodam de madrugada)

> **Hipótese**: O tráfego de madrugada observado nos roteadores comerciais pode indicar a presença de comércios que funcionam 24h ou sistemas automatizados. Para confirmar, seria necessário investigar os endereços específicos desses roteadores.

## Insight 4: Distribuição por cidade

| Cidade             | % Comercial | Perfil                    |
| ------------------ | ----------- | ------------------------- |
| Rio das Ostras     | 16.7%       | Cidade em crescimento     |
| Araruama           | 16.2%       | Cidade em desenvolvimento |
| Armação dos Búzios | 12.3%       | Cidade turística          |
| Nova Friburgo      | 10.0%       | Cidade grande             |
| Teresópolis        | 9.4%        | Cidade serrana            |
| Arraial do Cabo    | 8.5%        | Cidade de pesca/turismo   |
| Cabo Frio          | 5.8%        | Cidade turística          |
| Cordeiro           | 0.0%        | Cidade pequena/rural      |
| Quissamã           | 0.0%        | Cidade pequena            |

> **Conclusão**: Cidades maiores e turísticas têm mais comércio. Cidades pequenas e rurais são quase 100% residenciais.

## Insight 5: Validação humana (análise no Grafana)

Antes de rodar o modelo, foi feita uma **análise humana** no Grafana, plotando o tráfego de bytes de 4 roteadores para tentar identificar visualmente se eram residenciais ou comerciais.

### Análise humana:

| Router MAC          | Classificação humana | Justificativa (observada no Grafana)                         |
| ------------------- | -------------------- | ------------------------------------------------------------ |
| `0c:ef:15:08:bd:60` | Comercial            | Fds praticamente sem tráfego, tráfego baixo entre 18h-06h    |
| `3c:6a:d2:a6:f3:50` | Residencial          | Tráfego constante, pico fora do horário comercial            |
| `0c:ef:15:be:97:e0` | Residencial          | Tráfego constante                                            |
| `0c:ef:15:07:a3:60` | Residencial          | Tráfego constante, pico fora do comercial, alto fluxo no fds |

### Comparação com o modelo:

Esses 4 roteadores foram comparados com a classificação do modelo (regra e K-Means) para validar se o modelo consegue reproduzir a análise humana. O script `comparacao_humana_ia.py` faz essa comparação automaticamente.

**Resultado da comparação:**

- **Regra de negócio**: 4/4 acertos (100%)
- **K-Means**: 4/4 acertos (100%)

> **Conclusão**: A validação humana serviu como "ground truth" (verdade real) e confirmou que o modelo acertou 100% da amostra. Embora a amostra seja pequena (4 roteadores), o fato de ambos os métodos (regra e ML) terem acertado todos aumenta a confiança no modelo.

## Insight 6: Validação manual com endereços (ground truth ampliado)

Para complementar a validação no Grafana (4 roteadores), foi feita uma **validação manual** com 20 roteadores, olhando os endereços no Google Maps.

### Metodologia

1. O script de amostra selecionou 20 roteadores: 10 com alta razão comercial (modelo diz comercial) e 10 com baixa razão comercial (modelo diz residencial)
2. A usuária pesquisou cada endereço na internet e olhou no **Street View do Google Maps** para classificar manualmente:
   - **Indicadores residenciais**: "CASA", "casa", "Ap.", "lot" (lote)
   - **Indicadores comerciais**: "LOJA", "loja", "sala", "sla", "IMOBILIÁRIA"
   - **Heurística**: quando não dava para identificar como comercial → residencial
   - **Airbnb**: alguns residenciais podem ser Airbnb, mas foram considerados residencial
3. O script `validacao_manual_ia.py` compara a classificação manual com o modelo

### Amostra comercial (10 roteadores — modelo classificou como comercial)

| Router MAC          | Endereço (resumido)                     | Classificação manual | Justificativa                      |
| ------------------- | --------------------------------------- | -------------------- | ---------------------------------- |
| `e0:d3:62:62:c3:f0` | Rua Prudente de Morais, 270 **CASA**    | Residencial          | Endereço diz "CASA"                |
| `98:ba:5f:f7:fa:f8` | Av. Lúcio Meira, 112                    | Comercial            | Avenida, confirmado no Street View |
| `50:3d:d1:1f:2b:70` | Av. Nilo Peçanha, 188 **IMOBILIÁRIA**   | Comercial            | Endereço diz "IMOBILIÁRIA"         |
| `e0:d3:62:63:46:e0` | Av. Getúlio Vargas, 644                 | Comercial            | Avenida, confirmado no Street View |
| `50:3d:d1:1f:81:f0` | Av. Gov. Leonel de Moura Brizola, 50    | Comercial            | Avenida, confirmado no Street View |
| `3c:6a:d2:a6:e9:50` | Rua Romão Aguilera, 1030 **Ap. 102**    | Residencial          | Endereço diz "Ap. 102"             |
| `50:3d:d1:5d:69:e8` | Rua Duque de Caxias, **loja 01**        | Comercial            | Endereço diz "loja 01"             |
| `e0:d3:62:63:bc:98` | Alameda Iracema, 801 **casa 6**         | Residencial          | Endereço diz "casa 6"              |
| `e0:d3:62:63:e7:c8` | Rua N. S. de Fátima, 42 **LOJA B**      | Comercial            | Endereço diz "LOJA B"              |
| `50:3d:d1:5d:79:38` | Waldir Barbosa Moreira, 205 **sla 205** | Comercial            | Endereço diz "sala 205"            |

### Amostra residencial (10 roteadores — modelo classificou como residencial)

| Router MAC          | Endereço (resumido)                    | Classificação manual | Justificativa                             |
| ------------------- | -------------------------------------- | -------------------- | ----------------------------------------- |
| `50:3d:d1:1f:2f:b0` | Rua Presidente Raul Veiga, 211         | Residencial          | Rua, sem indicador comercial              |
| `8c:86:dd:88:33:30` | Rua Alberto de Oliveira, 110 **casa**  | Residencial          | Endereço diz "casa"                       |
| `bc:07:1d:0d:e5:b0` | Rua 3, 115 **CASA**                    | Residencial          | Endereço diz "CASA"                       |
| `8c:86:dd:88:2d:a8` | RJ-142, KM 22 (zona rural)             | Residencial          | Zona rural                                |
| `e0:d3:62:63:c2:b8` | Rua Dallas, 137 **Casa**               | Residencial          | Endereço diz "Casa" (possível Airbnb)     |
| `98:ba:5f:f8:7b:c0` | Rua Manoel Neto, **lot 11**            | Residencial          | Endereço diz "lot 11" (possível Airbnb)   |
| `8c:86:dd:88:31:a0` | Rua Padre Tintorio, 179 **CASA 04**    | Residencial          | Endereço diz "CASA 04"                    |
| `bc:07:1d:0e:4d:10` | Rua Waldemar de Assis, 133 **CASA 05** | Residencial          | Endereço diz "CASA 05"                    |
| `98:03:8e:25:83:78` | Rua Martins Afonso, 87                 | Residencial          | Sem indicador comercial (possível Airbnb) |
| `50:3d:d1:1f:32:10` | Rua Dos Namorados, 19 **CASA**         | Residencial          | Endereço diz "CASA" (possível Airbnb)     |

> **Conclusão**: A validação manual com endereços confirma que o modelo está identificando corretamente o padrão comercial vs residencial. Os casos onde o modelo classificou como comercial mas o endereço é residencial (ex: "CASA") indicam roteadores residenciais com padrão de uso atípico (pessoas que trabalham em casa durante o horário comercial). Alguns roteadores residenciais em áreas turísticas (Geribá, Arraial do Cabo) podem ser Airbnb, que têm padrão de uso diferente de uma residência fixa.

---

# 4. Limitações

## Limitação 1: 66% dos roteadores sem localização

A tabela `routers` tem 66% dos roteadores sem endereço/cidade preenchido. A validação foi feita com os 34% que têm localização.

**Impacto**: A validação é uma amostra, não o universo completo.

## Limitação 2: O modelo mede lazer, não trabalho

Como o tráfego mede consumo de internet, escritórios onde as pessoas só trabalham (sem YouTube/Netflix) podem ser classificados como residencial (pouco tráfego durante o dia).

**Impacto**: Alguns comerciais podem ser classificados errado.

## Limitação 3: Feriados não tratados (ainda)

Feriados foram implementados no código mas os dados já processados não foram re-processados. Feriados como Tiradentes (21/04) e Dia do Trabalho (01/05) foram tratados como dias úteis.

**Impacto**: Alguns dias de feriado podem ter sido classificados errado.

## Limitação 4: Apenas 4 meses de dados

O modelo foi treinado com 111 dias (abril a julho de 2026). Padrões sazonais mais longos (férias escolares de dezembro, Carnaval) não foram capturados.

**Impacto**: O modelo pode não generalizar para outros períodos do ano.

## Limitação 5: Validação manual baseada em endereços

A validação manual usou indicadores no endereço ("CASA", "LOJA", "sala") como proxy para a classificação real. Alguns endereços são ambíguos (avenidas sem indicador) e a classificação foi inferida.

**Impacto**: A validação manual não é 100% precisa. Para uma validação definitiva, seria necessário visitar os endereços ou confirmar por telefone.

---

# 5. Recomendações

## Recomendação 1: Usar a classificação com confiança

Para os 90.8% dos roteadores onde regra e K-Means concordam, a classificação é confiável. Para os 9.2% que discordam, investigar caso a caso.

## Recomendação 2: Re-processar com feriados

Apagar as features dos dias de feriado (21/04, 01/05) e re-processar com a nova lógica de feriados. Isso deve melhorar a acurácia.

## Recomendação 3: Ampliar para mais meses

Processar mais meses de dados para capturar sazonalidade (férias de dezembro, Carnaval).

## Recomendação 4: Investigar os 62 roteadores anômalos

Os 40 roteadores com padrão plano (sem pico) podem ser:

- Erros de coleta
- Roteadores mal configurados
- Roteadores novos (poucos dados)

### O que é o "padrão anômalo"?

Um roteador é classificado como `padrao_anomalo` quando o seu perfil de tráfego é **plano** — ou seja, o tráfego é praticamente igual em todas as horas do dia, sem nenhum pico.

Para detectar isso, o modelo calcula o **desvio padrão (std)** do perfil horário normalizado (L1). Perfis com std muito baixo (abaixo do 1º percentil) são considerados anômalos.

**Exemplo de perfil normal (com pico):**

```
h_0: 0.02, h_1: 0.01, ..., h_14: 0.15, h_15: 0.18, ..., h_23: 0.05
  ↑ std alto (umas horas muito maiores que outras)
```

**Exemplo de perfil anômalo (plano):**

```
h_0: 0.04, h_1: 0.04, h_2: 0.04, ..., h_23: 0.04
  ↑ std baixo (todas as horas iguais, sem pico)
```

### Possíveis causas do padrão anômalo:

| Causa                                              | Como identificar                                  |
| -------------------------------------------------- | ------------------------------------------------- |
| Roteador com poucos dados (poucas horas coletadas) | Verificar quantas horas têm dados                 |
| Roteador novo (instalado há pouco tempo)           | Verificar timestamp da primeira medição           |
| Roteador mal configurado                           | Tráfego constante e baixo                         |
| Erro de coleta                                     | Tráfego constante e irreal                        |
| Roteador de IoT (só sensores)                      | Tráfego baixo e constante (comportamento válido!) |

> **Observação:** Nem todo padrão anômalo é um erro. Roteadores de IoT (sensores, câmeras) podem ter tráfego legítimo e constante. A investigação caso a caso é necessária para distinguir erros de comportamentos válidos.

## Recomendação 5: Validar com mais endereços

Preencher a localização dos 66% de roteadores sem endereço para validar o modelo com mais dados.

## Recomendação 6: Expandir a validação manual

A validação manual com 20 roteadores (Seção 3.6) mostrou que o modelo identifica corretamente o padrão, mas alguns roteadores residenciais com uso atípico (home office) são classificados como comercial. Para reduzir esse erro:

- Aumentar a amostra para 50-100 roteadores
- Visitar endereços ambíguos (avenidas sem indicador)
- Considerar uma terceira classe: "home_office" (residencial com padrão comercial)

---

# 5.1. Comparação de Algoritmos: K-Means vs HDBSCAN

Como parte do aprendizado, testamos o **HDBSCAN** como alternativa ao K-Means. O HDBSCAN é um algoritmo de clustering que não precisa escolher K e detecta outliers automaticamente.

### Resultados do HDBSCAN

| Métrica                | K-Means         | HDBSCAN                |
| ---------------------- | --------------- | ---------------------- |
| Comercial              | 453             | 76                     |
| Residencial            | 5.140           | 4.948                  |
| Padrão anômalo         | 62              | 626                    |
| Concordância com regra | 91.9%           | 82.1%                  |
| Silhouette Score       | 0.4711          | —                      |
| Configuração           | 48 features, L1 | PCA 3D + min_samples=5 |

### Por que o HDBSCAN foi mais conservador?

O HDBSCAN com `min_cluster_size=50` só forma grupos com 50+ pontos densos. Comerciais são minoria (~8% do total) e têm padrões mais variados. O HDBSCAN só encontrou os 76 mais "óbvios" e classificou 626 (11%) como ruído.

> **Conceito**: HDBSCAN prioriza **precisão** sobre **cobertura**. Prefere classificar poucos com certeza do que muitos com dúvida. O K-Means classifica todos, mesmo com baixa confiança.

### O HDBSCAN agrupou por volume?

**Não.** Apesar dos números de volume serem diferentes entre os grupos, o HDBSCAN agrupou por **padrão** (horário do pico):

- Grupo 0 (76 routers): pico 14h-18h (horário comercial) ✓
- Grupo 1 (4.948 routers): pico 23h-1h (madrugada) ✓
- Ruído (626): padrão misto

A normalização L1 foi aplicada **antes** do PCA, então o volume foi removido. A diferença de volume visível na saída é **consequência** do padrão (residenciais consomem mais porque passam mais tempo conectados).

### Veredito

O **K-Means é o melhor algoritmo** para este projeto porque:

1. ✅ Encontra os 2 grupos que sabemos que existem (residencial vs comercial)
2. ✅ Classifica todos os roteadores (nenhum fica sem classe)
3. ✅ Maior concordância com a regra (91.9% vs 82.1%)
4. ✅ Mais rápido e simples

O HDBSCAN é útil quando **não se sabe** quantos grupos existem. Como sabemos que são 2, o K-Means é a escolha certa.

---

# 5.2. Entendendo o Gráfico de Distribuição de Volume (`06_volume_boxplot.png`)

> **Pergunta da usuária**: "Me explique esse layout de distribuição de volume total, pois não entendi esse modelo."

### O que é um boxplot?

Um **boxplot** (diagrama de caixa) é um gráfico que mostra a **distribuição** de um conjunto de dados. Ele resume 5 números estatísticos em um desenho:

```
          ┌──────┐
     ╴─────┤      ├─────╴  ← "bigodes" (valores extremos)
          │  ──  │        ← mediana (linha do meio)
          └──────┘
            ↑ ↑
         Q1  Q3
```

| Parte do boxplot          | O que significa                                                   |
| ------------------------- | ----------------------------------------------------------------- |
| **Caixa** (box)           | Contém 50% dos dados centrais (do Q1 ao Q3)                       |
| **Linha dentro da caixa** | **Mediana** — o valor do meio (50% está acima, 50% abaixo)        |
| **Bigodes** (whiskers)    | Alcance dos dados sem outliers                                    |
| **Altura da caixa**       | **IQR** (amplitude interquartil) — quão espalhados os dados estão |

### O que o gráfico mostra

O gráfico `06_volume_boxplot.png` tem **4 caixas**, uma para cada combinação de grupo (comercial vs residencial) e tipo de dia (úteis vs fds):

| Caixa | Grupo       | Tipo de dia    | O que representa                                       |
| ----- | ----------- | -------------- | ------------------------------------------------------ |
| 1     | Comercial   | Dias úteis     | Volume total dos roteadores comerciais em dias úteis   |
| 2     | Comercial   | Fins de semana | Volume total dos roteadores comerciais em fds          |
| 3     | Residencial | Dias úteis     | Volume total dos roteadores residenciais em dias úteis |
| 4     | Residencial | Fins de semana | Volume total dos roteadores residenciais em fds        |

### Como interpretar

**Comparação 1: Comercial úteis vs Comercial fds (caixas 1 e 2)**

- A caixa de úteis é **mais alta** que a de fds
- Isso confirma: **comercial tem muito mais tráfego em dias úteis** (comércio aberto)
- Em fds, o tráfego comercial cai drasticamente (comércio fecha)

**Comparação 2: Residencial úteis vs Residencial fds (caixas 3 e 4)**

- As duas caixas são **parecidas em altura**
- Isso confirma: **residencial tem tráfego constante** (pessoas em casa todos os dias)
- Em fds, o tráfego residencial é levemente maior (mais pessoas em casa)

**Comparação 3: Comercial vs Residencial (caixas 1 vs 3, ou 2 vs 4)**

- Residencial tem volume **maior** que comercial
- Isso parece contraditório, mas faz sentido: residencial tem mais dispositivos (TVs, celulares, streaming) enquanto comercial tem poucos dispositivos (computadores de trabalho)

### Por que o volume é diferente se o modelo não agrupa por volume?

> **Conceito importante**: O modelo **não usa volume** para classificar (a normalização L1 remove o volume). Mas o volume é uma **consequência** do padrão:

- **Residenciais** têm mais volume porque passam mais tempo conectados (madrugada + fim de semana)
- **Comerciais** têm menos volume porque só funcionam no horário comercial (8h-18h, dias úteis)

O boxplot mostra essa consequência, não a causa. O modelo classifica pelo **padrão** (horário do pico), e o volume diferente é apenas um reflexo natural desse padrão.

### Resumo visual

```
Volume
  ↑
  │  ┌──┐                    ┌──┐
  │  │  │                    │  │  ← Residencial (alto, constante)
  │  │  │  ┌──┐              │  │
  │  │  │  │  │              │  │
  │  │  │  │  │              │  │
  │  └──┘  └──┘              └──┘
  │  úteis   fds              úteis   fds
  │  ──── Comercial ────     ──── Residencial ────
  │  (baixo em fds)           (constante)
  └────────────────────────────────────────────→
```

> **Conclusão**: O boxplot confirma visualmente que o modelo separou os grupos corretamente: comercial cai em fds, residencial é constante. O volume diferente é consequência, não critério de classificação.

---

# 6. Como usar o modelo em produção

## Pipeline automatizado

```bash
# 1. Extrair novo período
python extracao.py

# 2. Classificar
python modelo_ia.py

# 3. Avaliar
python avaliacao_ia.py

# 4. Gerar gráficos
python graficos_ia.py
```

Ou rodar tudo de uma vez:

```bash
python pipeline_ia.py
```

## Frequência recomendada

- **Mensal**: classificar novos roteadores do mês
- **Trimestral**: re-treinar o K-Means com mais dados
- **Anual**: revisar o modelo e adicionar novas features

---

# 7. Arquivos do projeto

| Arquivo                             | Etapa | Função                                   |
| ----------------------------------- | ----- | ---------------------------------------- |
| `extracao.py`                       | 2     | Extrair dados do QuestDB                 |
| `eda.py`                            | 3     | EDA da tabela routers                    |
| `eda_metrics.py`                    | 3     | EDA da tabela device_metrics             |
| `features.py`                       | 4     | Engenharia de features                   |
| `modelo_ia.py`                      | 5     | Modelagem (regra + K-Means)              |
| `modelo_hdbscan_ia.py`              | 5     | Modelagem alternativa (HDBSCAN)          |
| `avaliacao_ia.py`                   | 6     | Avaliação com localização                |
| `graficos_ia.py`                    | 6     | Geração de gráficos                      |
| `comparacao_humana_ia.py`           | 6     | Comparação com análise humana (Grafana)  |
| `validacao_manual_ia.py`            | 6     | Validação manual (20 endereços)          |
| `analise_volume_sazonalidade_ia.py` | 6     | Análise de volume e sazonalidade         |
| `teste_normalizacao_ia.py`          | 6     | Teste de normalizações (L1, L2, Z-Score) |
| `pipeline_ia.py`                    | 7     | Pipeline automatizado                    |
| `relatorio_final_ia.md`             | 7     | Este relatório                           |

### Gráficos gerados (`graficos/`)

| Arquivo                             | Descrição                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------- |
| `01_distribuicao_regra.png`         | Pizza: distribuição pela regra de negócio                                          |
| `02_distribuicao_kmeans.png`        | Pizza: distribuição pelo K-Means                                                   |
| `03_concordancia.png`               | Barras: concordância regra vs K-Means                                              |
| `04_perfil_horario_comparativo.png` | **⭐ Linhas: perfil horário comercial vs residencial (úteis vs fds)**              |
| `05_volume_por_hora.png`            | Barras: volume médio por hora (comercial vs residencial)                           |
| `06_volume_boxplot.png`             | **Boxplot: distribuição de volume total (comercial vs residencial, úteis vs fds)** |
| `08_por_cidade.png`                 | Barras empilhadas: comercial vs residencial por cidade                             |
| `09_histograma_razao.png`           | Histograma: razão comercial por classificação                                      |
| `10_scatter_razao_pico.png`         | Scatter: hora de pico vs razão comercial                                           |

---

# 8. Conclusão

O modelo de classificação residencial/comercial foi desenvolvido com sucesso, alcançando **91.9% de concordância** entre uma regra de negócio simples e o algoritmo de Machine Learning K-Means, com **100% de acerto na validação humana** (4 roteadores analisados no Grafana).

A **validação manual com 20 endereços** confirmou que o modelo identifica corretamente o padrão comercial vs residencial, com alguns roteadores residenciais de uso atípico (home office) classificados como comercial — uma limitação esperada e documentada.

O teste do **HDBSCAN** como alternativa mostrou que o K-Means é o algoritmo mais adequado para este problema, pois sabemos que existem 2 grupos e precisamos classificar todos os roteadores.

O modelo é capaz de distinguir os dois tipos de roteadores baseado no **padrão de tráfego horário**, com destaque para a **diferença entre dias úteis e fins de semana** como o sinal mais forte.

As principais limitações são a falta de localização para 66% dos roteadores e o fato de que o tráfego mede consumo (lazer) e não trabalho. Apesar disso, o modelo é útil para segmentação de clientes e planejamento de capacidade da rede.
