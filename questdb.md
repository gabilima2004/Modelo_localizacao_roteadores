# QuestDB — Conceitos e Detalhes de Conexão

> Este documento explica os conceitos do QuestDB relevantes para o projeto,
> com foco na conexão e nas diferenças em relação a bancos relacionais tradicionais.

---

# 1. O que é o QuestDB?

QuestDB é um **banco de dados de séries temporais** (time-series database) de código aberto, projetado para armazenar e consultar dados com **timestamps** de forma extremamente rápida.

### Por que não usar PostgreSQL "normal"?

|                       | PostgreSQL                   | QuestDB                       |
| --------------------- | ---------------------------- | ----------------------------- |
| **Otimizado para**    | Dados transacionais (OLTP)   | Dados temporais (time-series) |
| **Inserção**          | Uma linha por vez            | Lotes (batch) ultra-rápidos   |
| **Queries temporais** | Lentas sem índices complexos | Nativo e otimizado            |
| **Armazenamento**     | Baseado em linhas            | Baseado em colunas            |
| **Volume**            | Milhões de linhas            | Bilhões de linhas             |

> **No projeto:** temos ~864 milhões de linhas de métricas. Um banco tradicional engasgaria. O QuestDB foi feito para isso.

---

# 2. Portas do QuestDB

QuestDB escuta em **várias portas simultaneamente**, cada uma para um protocolo diferente:

| Porta    | Protocolo       | Biblioteca Python | Para que serve                        |
| -------- | --------------- | ----------------- | ------------------------------------- |
| **9000** | HTTP (REST API) | `requests`        | Console web, queries via HTTP         |
| **8812** | PostgreSQL wire | `psycopg2`        | Conexões SQL via protocolo PostgreSQL |
| **9009** | InfluxDB line   | `requests`        | Ingestão rápida de dados (escrita)    |
| **9003** | Min health      | —                 | Health checks (monitoramento)         |
| **9001** | Prometheus      | —                 | Métricas de monitoramento             |

### Qual porta usar no projeto?

Usamos a **porta 8812** com `psycopg2` porque:

1. **psycopg2** é a biblioteca PostgreSQL mais madura e estável no Python
2. Permite usar **SQL padrão** para consultar os dados
3. Retorna os dados em formato de dicionário (com `RealDictCursor`), fácil de converter para DataFrame
4. É a forma mais **familiar** para quem já conhece PostgreSQL

### E a porta 9000?

A porta 9000 é a interface HTTP do QuestDB. Você pode fazer queries assim:

```python
import requests

response = requests.get(
    "http://localhost:9000/exec",
    params={"query": "SELECT * FROM routers LIMIT 5"}
)
data = response.json()
```

**Vantagens da porta 9000:**

- Não precisa de biblioteca especial (só `requests`)
- Retorna JSON, fácil de processar

**Desvantagens:**

- Não tem cursor (precisa carregar tudo na memória de uma vez)
- Menos eficiente para resultados grandes
- Não suporta parâmetros bind (precisa concatenar strings — risco de SQL injection)

> **No projeto:** usamos a porta 8812 porque precisamos de cursores para iterar sobre resultados grandes e queremos a segurança do psycopg2.

---

# 3. QuestDB é Single-Database

### Diferença fundamental do PostgreSQL tradicional

No PostgreSQL tradicional:

```sql
-- Você pode criar múltiplos bancos
CREATE DATABASE vendas;
CREATE DATABASE rh;
CREATE DATABASE estoque;

-- E conectar a cada um
\c vendas    -- conecta ao banco vendas
\c rh        -- conecta ao banco rh
```

No QuestDB:

```
— NÃO existe o conceito de múltiplos bancos de dados
— Uma instância = um banco = todas as tabelas juntas
— Não há CREATE DATABASE
— Não há \c para trocar de banco
```

### Por que?

QuestDB foi projetado para **alta performance** com dados temporais. A arquitetura de armazenamento em colunas e a indexação por timestamp funcionam de forma diferente dos bancos relacionais. Manter tudo em um único "namespace" simplifica a engine e permite a velocidade que o QuestDB oferece.

### Impacto na conexão com psycopg2

O `psycopg2` exige o parâmetro `database` na conexão, porque ele foi feito para PostgreSQL tradicional (onde isso importa). No QuestDB, esse parâmetro é **ignorado** — qualquer valor funciona:

```python
# Todas essas conexões vão para o MESMO lugar:
psycopg2.connect(host="localhost", port=8812, user="admin", password="quest", database="qdb")
psycopg2.connect(host="localhost", port=8812, user="admin", password="quest", database="qualquer_coisa")
psycopg2.connect(host="localhost", port=8812, user="admin", password="quest", database="nao_importa")
```

> **Conclusão:** o parâmetro `database` precisa estar presente (o psycopg2 exige), mas o valor não faz diferença para o QuestDB.

---

# 4. Autenticação no QuestDB

### Credenciais padrão

Por padrão, o QuestDB vem com autenticação **desabilitada**. Isso significa:

- Qualquer `user` e `password` são aceitos
- Não há verificação real de identidade

As credenciais padrão na documentação são `admin` / `quest`, mas **qualquer valor funciona**:

```python
# Todas essas conexões funcionam (se autenticação estiver desabilitada):
psycopg2.connect(host="localhost", port=8812, user="admin", password="quest", database="qdb")
psycopg2.connect(host="localhost", port=8812, user="eu", password="123", database="qdb")
psycopg2.connect(host="localhost", port=8812, user="x", password="y", database="qdb")
```

### Quando a autenticação importa?

Se o administrador do QuestDB **habilitar autenticação** (recomendado em produção), então:

- Somente usuários cadastrados poderão conectar
- As credenciais precisam ser válidas
- É necessário configurar no arquivo `conf/server.conf` do QuestDB

> **No projeto:** como estamos em ambiente de desenvolvimento, a autenticação provavelmente está desabilitada. Mas é boa prática manter `user` e `password` no código — se a autenticação for habilitada no futuro, basta ajustar os valores.

---

# 5. Resumo prático para o projeto

### Configuração mínima necessária no psycopg2

```python
conn = psycopg2.connect(
    host="localhost",       # Obrigatório: onde o QuestDB está
    port=8812,              # Obrigatório: porta PostgreSQL wire (NÃO é 9000!)
    user="admin",           # Obrigatório: qualquer valor funciona (padrão: admin)
    password="quest",       # Obrigatório: qualquer valor funciona (padrão: quest)
    database="qdb",         # Obrigatório: qualquer valor funciona (QuestDB ignora)
    cursor_factory=RealDictCursor  # Opcional: retorna dicionários em vez de tuplas
)
```

### Parâmetros que NÃO existem no QuestDB

| Parâmetro do PostgreSQL | Funciona no QuestDB? | Por que?                   |
| ----------------------- | -------------------- | -------------------------- |
| `database`              | ⚠️ Ignorado          | QuestDB é single-database  |
| `schema` (public, etc.) | ❌ Não               | QuestDB não tem schemas    |
| `CREATE DATABASE`       | ❌ Não               | QuestDB é single-database  |
| `GRANT / REVOKE`        | ⚠️ Limitado          | Autenticação básica apenas |
| `VIEWS materializadas`  | ❌ Não               | QuestDB não suporta        |

### Queries que funcionam no QuestDB

```sql
-- ✅ Funciona: SELECT com WHERE, GROUP BY, ORDER BY
SELECT router_mac, AVG(bytes_up) FROM device_metrics
WHERE timestamp >= '2025-04-01' GROUP BY router_mac;

-- ✅ Funciona: Funções de agregação temporal (SAMPLE BY)
SELECT router_mac, AVG(bytes_up)
FROM device_metrics
WHERE timestamp >= '2025-04-01'
SAMPLE BY 1h ALIGN TO CALENDAR;

-- ✅ Funciona: JOIN entre tabelas
SELECT r.router_mac, r.city, d.bytes_up
FROM routers r
JOIN device_metrics d ON r.router_mac = d.router_mac
WHERE d.timestamp >= '2025-04-01';

-- ❌ Não funciona: CREATE DATABASE
CREATE DATABASE meu_banco;  -- QuestDB não suporta

-- ❌ Não funciona: ALTER TABLE ADD COLUMN
ALTER TABLE routers ADD COLUMN nova_coluna INT;  -- QuestDB não suporta
```

---

# 6. Dica: Como testar a conexão

Se quiser verificar se o QuestDB está acessível antes de rodar a extração completa:

```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host="localhost",
    port=8812,
    user="admin",
    password="quest",
    database="qdb",
    cursor_factory=RealDictCursor
)

# Testa com uma query simples
with conn.cursor() as cur:
    cur.execute("SELECT * FROM routers LIMIT 1")
    rows = cur.fetchall()
    print("Conexão OK!")
    print(f"Colunas: {rows[0].keys()}")

conn.close()
```

Se isso funcionar, sua conexão está correta e você pode rodar a extração completa.
