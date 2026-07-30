import pandas as pd

# Carregar os dados
#datai = "2026-04-01"
#dataf = "2026-04-02"

# Carregar os dados (dados brutos em data/raw/)
df_metrics = pd.read_csv("data/raw/metrics_2026-04-01.csv", parse_dates=["timestamp"])

# TODO: responda as perguntas acima usando estas funções:
# df_metrics.shape        → quantas linhas e colunas?
# df_metrics.dtypes       → quais os tipos?
# df_metrics.head()       → primeiras linhas

#info geral
#| Colunas de `device_metrics` | device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down, last_connected |

#num de linhas e colunas
def linha_coluna():
    return df_metrics.shape

#tipos das colunas
def tipos():
    return df_metrics.dtypes

#primeiras linhas

def primeiras_linhas():
    return df_metrics.head(50)

### Dados faltantes

# Quantos valores nulos existem em cada coluna?
def valores_nulos():
    # Pegar a quantidade de valores vazios na coluna desejada
     return df_metrics.isnull().sum()

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
#device_mac, router_mac, timestamp, bytes_up, bytes_down, packets_up, packets_down, last_connected |
#qtd de devices por roteador
#bytes por roteador
#packets por roteador
def estatisticas_bytesup():
    return df_metrics["bytes_up"].describe()

def estatisticas_bytesdown():
    return df_metrics["bytes_down"].describe()


def estatisticas_packetsup():
    return df_metrics["packets_up"].describe()

def estatisticas_packetsdown():
    return df_metrics["packets_down"].describe()

### Distribuições
# Roteadores por fabricante
def rot_dev():
    qtd = df_metrics.groupby("router_mac")["device_mac"].nunique()
    return qtd

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
    print("Bytes_up")
    print(estatisticas_bytesup())
    print("Bytes_down")
    print(estatisticas_bytesdown())
    print("Packets_up")
    print(estatisticas_packetsup())
    print("Packets_down")
    print(estatisticas_packetsdown())
    print("Devices")
    print(rot_dev())

if __name__ == "__main__":
    main()
    
