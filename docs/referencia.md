# Material de Referência e Estudo

> Teoria, documentação técnica e referências usadas no projeto.

---

# 1. Aprendizado Não Supervisionado (Clustering)

Existem três grandes categorias de Machine Learning:

## 1.1 Supervisionado

Você tem **rótulos** (respostas certas) nos dados de treino. O modelo aprende a mapear entrada → rótulo.

> Exemplo: você tem 1000 fotos **rotuladas** como "gato" ou "cachorro". O modelo aprende a distinguir.

## 1.2 Não supervisionado

Você **não tem rótulos**. O modelo encontra **estrutura/padrões** nos dados por conta própria.

> Exemplo: você tem dados de clientes sem nenhuma categoria. O modelo agrupa clientes parecidos.

## 1.3 Reforço

O modelo aprende por **tentativa e erro** recebendo recompensas/punições.

---

# 2. K-Means (o algoritmo usado)

## Como funciona:

1. Você escolhe **K** (número de grupos, ex: 2)
2. O algoritmo coloca **K pontos aleatórios** (centroides) no espaço
3. Cada roteador é atribuído ao **centroide mais próximo**
4. Os centroides se **movem** para o centro de seus grupos
5. Repete passos 3-4 até convergir (centroides param de mover)

## Parâmetros do scikit-learn:

| Parâmetro      | O que faz                               | Valor usado |
| -------------- | --------------------------------------- | ----------- |
| `n_clusters`   | Número de grupos (K)                    | 2           |
| `random_state` | Semente aleatória (reproduzível)        | 42          |
| `n_init`       | Roda 10 vezes com centroides diferentes | 10          |

## Silhouette Score

Mede quão bem separados os grupos estão:

- **Próximo de 1** → grupos bem separados ✅
- **Próximo de 0** → grupos sobrepostos ⚠️
- **Negativo** → pontos no grupo errado ❌

---

# 3. Outros Algoritmos de Clustering

| Algoritmo           | Precisa K? | Lida com outliers? | Velocidade     | Recomendação           |
| ------------------- | ---------- | ------------------ | -------------- | ---------------------- |
| **K-Means** (usado) | ✅ Sim     | ❌ Não             | ⚡ Rápido      | ✅ Funciona bem        |
| **HDBSCAN**         | ❌ Não     | ✅ Sim             | 🐢 Médio       | ⭐ Melhor alternativa  |
| **DBSCAN**          | ❌ Não     | ✅ Sim             | ⚡ Rápido      | ⭐ Boa opção           |
| **GMM**             | ✅ Sim     | ❌ Não             | ⚡ Rápido      | ⚠️ Para probabilidades |
| **Hierarchical**    | ❌ Não     | ⚠️ Parcial         | 🐢 Muito lento | ❌ Não escala          |
| **K-Medoids**       | ✅ Sim     | ✅ Sim             | 🐢 Médio       | ⚠️ Para interpretar    |

---

# 4. Estatísticas

## Média (Mean)

A soma de todos os valores dividida pela quantidade.
$$\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i$$
⚠️ **Problema:** sensível a outliers.

## Mediana

O valor do "meio" quando os dados estão ordenados. **Ignora outliers**.

## Desvio Padrão (Standard Deviation)

A **raiz quadrada da variância**. Mede quão "espalhados" os dados estão.
$$s = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2}$$

- Desvio **baixo** → dados concentrados perto da média
- Desvio **alto** → dados espalhados

## Coeficiente de Variação (CV)

O desvio padrão **dividido pela média**. Mede variabilidade **relativa** (sem unidade).
$$CV = \frac{s}{\bar{x}}$$

---

# 5. Machine Learning vs Programação Tradicional

|                           | Programação tradicional     | Machine Learning                         |
| ------------------------- | --------------------------- | ---------------------------------------- |
| **Quem escreve a regra?** | Você, humano                | O algoritmo descobre                     |
| **O que você dá?**        | As regras + os dados        | Os dados + as respostas                  |
| **Exemplo**               | `if tráfego > X: comercial` | "Aqui estão exemplos, descubra o padrão" |

No projeto:

- **Regra de negócio** (NÃO é ML): `if razao_comercial > 0.5: comercial`
- **K-Means** (É ML): agrupa sozinho, depois interpretamos

---

# 6. QuestDB

## Portas

| Porta    | Protocolo       | Para que serve                           |
| -------- | --------------- | ---------------------------------------- |
| **9000** | HTTP (REST API) | Console web, queries via HTTP            |
| **8812** | PostgreSQL wire | Conexões com psycopg2 (usado no projeto) |
| **9009** | InfluxDB line   | Ingestão de dados                        |

## Single-Database

QuestDB **não tem o conceito de múltiplos bancos**. O parâmetro `database` no psycopg2 é **ignorado**.

## Autenticação

Por padrão, a autenticação está **desabilitada**. Qualquer `user` e `password` funcionam.

## Diferenças do PostgreSQL

- ❌ Não suporta `HAVING` (usar subqueries)
- ❌ Não suporta `CREATE DATABASE`
- ❌ Não tem schemas
- ✅ Suporta `SAMPLE BY` (agregação temporal)

---

# 7. Pandas (Conceitos-chave)

## DataFrame vs Series

- **DataFrame**: tabela (planilha) com linhas e colunas
- **Series**: uma coluna da tabela (com rótulos)

## groupby

```python
df.groupby("coluna_para_agrupar")["coluna_para_calcular"].função()
```

Agrupa os dados por uma coluna e aplica uma função (sum, mean, count).

## pivot_table

Transforma dados de formato longo para largo:

```python
df.pivot_table(index="router_mac", columns="hora", values="trafego", fill_value=0)
```

## join

Junta dois DataFrames pelo índice:

```python
df1.join(df2, how="inner")  # só quem existe nos dois
df1.join(df2, how="outer")  # mantém todos
```

## Normalização L1

```python
soma = perfil.sum(axis=1)           # soma cada linha
perfil_norm = perfil.div(soma, axis=0)  # divide cada linha pela sua soma
```

Cada perfil vira uma distribuição que soma 1. Comparamos a "forma", não o tamanho.
