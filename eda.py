import pandas as pd

# Carregar os dados (dados brutos em data/raw/)
df_routers = pd.read_csv("data/raw/routers.csv", parse_dates=["timestamp"])

# TODO: responda as perguntas acima usando estas funções:
# df_routers.shape        → quantas linhas e colunas?
# df_routers.dtypes       → quais os tipos?
# df_routers.head()       → primeiras linhas

#info geral
#| Colunas de `routers` | router_mac, manufacturer, model, location, city, state, latitude, longitude |
#| Colunas de `device_metrics` | device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down, last_connected |

#num de linhas e colunas
def linha_coluna():
    return df_routers.shape

#tipos das colunas
def tipos():
    return df_routers.dtypes

#primeiras linhas

def primeiras_linhas():
    return df_routers.head(50)

### Dados faltantes

# Quantos valores nulos existem em cada coluna?
def valores_nulos():
    # Pegar a quantidade de valores vazios na coluna desejada
    #quantidade_vazios = df_routers['router_mac', 'manufacturer', 'model', 'location', 'city', 'state', 'latitude', 'longitude'].isnull().sum()
    #return quantidade_vazios
    return df_routers.isnull().sum()

# Tem coluna que está quase toda vazia?
def col_vazias():
    dim = linha_coluna()
    linha = dim[0]
    col = dim[1]
    parametro = linha*0.8
    #eu tenho só o valor total de vazios?
    qtd_vazios = valores_nulos()
    col_vazias = []
    for i,j in qtd_vazios.items():
        if j > parametro:
            col_vazias += [i]
    return col_vazias


### Estatísticas descritivas
#Média, mediana, mínimo, máximo das colunas numéricas (latitude, longitude)
#Valores únicos das colunas de texto (city, state, manufacturer)
# acho que isso nao faz sentido para routers
def estatisticas_lat():
    return df_routers["latitude"].describe()

def estatisticas_long():
    return df_routers["longitude"].describe()

### Distribuições
# Roteadores por fabricante
def rot_fab():
    qtd = df_routers["manufacturer"].value_counts()
    return qtd

# Roteadores por modelo
def rot_mod():
    qtd = df_routers["model"].value_counts()
    return qtd

# Roteadores por estado
def rot_estado():
    qtd = df_routers["state"].value_counts()
    return qtd

# Roteadores por cidade 
def rot_cidade():
    qtd = df_routers["city"].value_counts()
    return qtd

def latitudes_invalidas():
    # Filtra roteadores com latitude inválida (fora do Brasil: < -33 ou > 5)
    # Usa vetorização do pandas (sem loop for) — mais rápido e idiomático

    # 1. Cria máscara: True onde latitude é inválida
    #    notna() remove nulos (NaN não é inválido, é ausente)
    #    (latitude > 5) | (latitude < -33) identifica fora do intervalo válido
    mascara = df_routers["latitude"].notna() & \
              ((df_routers["latitude"] > 5) | (df_routers["latitude"] < -33))

    # 2. Aplica a máscara no DataFrame para pegar as linhas inválidas
    df_invalidos = df_routers[mascara]

    # 3. Retorna a quantidade e os dados dos roteadores inválidos
    print(f"Quantidade de roteadores com latitude inválida: {len(df_invalidos)}")
    if len(df_invalidos) > 0:
        print("Roteadores inválidos:")
        print(df_invalidos[["router_mac", "latitude", "longitude", "city"]])
    return df_invalidos



def main ():
    print("Estatísticas básicas")
    print("Quantidade de linhas e colunas")
    l = linha_coluna()[0]
    c = linha_coluna()[1]
    print(f"linha = {l}")
    print(f"coluna = {c}")
    print("Tipos das colunas")
    print(tipos())
    print("50 primeiras linhas")
    print(primeiras_linhas())
    print("Quantidade de valores nulos")
    print(valores_nulos())
    print("Colunas vazias")
    print(col_vazias())
    print("Estatísticas")
    print(f"Latitude: {estatisticas_lat()}")
    print(f"Longitude: {estatisticas_long()}")
    print("Agrupamentos")
    print("Roteadores por fabricante")
    print(rot_fab())
    print("Roteadores por modelo")
    print(rot_mod())
    print("Roteadores por estado")
    print(rot_estado())
    print("Roteadores por cidade")
    print(rot_cidade())
    print("Latitudes inválidas")
    print(latitudes_invalidas())


if __name__ == "__main__":
    main()
    
