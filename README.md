# TCP sobre UDP
## Estrutura dos arquivos
```
common.py   → constantes e funções de empacotamento compartilhadas
client.py   → lado que envia os dados (produtor)
server.py   → lado que recebe os dados (consumidor, simula perdas)
```

## common.py

Define as variáveis e funções (pack e unpack) que cliente e servidor usam.

```python
MSS = 1024 # tamanho máximo de um segmento
HDR = 8 # cabeçalho
MAX_PKT = 1032 # MSS + HDR
CWND0 = MSS  # janela inicial (1 segmento)
SSTHRESH0 = 15360 # limiar inicial do slow start (15 MSS)
RTO = 0.5 # timeout de retransmissão em segundos
MOD = 65536  # números de sequência são 16 bits (0–65535)
```

### `pack()` — monta um segmento

```python
def pack(seq, ack, dlen, data=b'', A=0, S=0, F=0):
    flags = (dlen << 3) | (A << 2) | (S << 1) | F
    return struct.pack('!HHHH', seq % MOD, ack % MOD, 0, flags) + data
```

Empacota tudo em 8 bytes de cabeçalho. As flags `A` (ACK), `S` (SYN) e `F` (FIN) dividem o mesmo campo `flags` junto com o `dlen`. O `% MOD` garante que o número de sequência fique em 16 bits.

### `unpack()` — decodifica um segmento recebido

Faz o caminho inverso e devolve um dicionário com `seq`, `ack`, `dlen`, `A`, `S`, `F` e `payload`. Qualquer segmento menor que 8 bytes retorna `None`.

---

## client.py

### Three-way handshake

```
cliente  →  SYN (S=1)
servidor →  SYN-ACK (S=1, A=1)
cliente  →  ACK (A=1)
```

O ISN (Initial Sequence Number) do cliente é sorteado aleatoriamente. O SYN consome um número de sequência, então os dados começam em `isn + 1`.

### O loop principal de envio

Cada iteração do `while base < total` é um RTT. O fluxo é:

1. **Monta e envia a janela** — até `cwnd` bytes a partir de `base`
2. **Espera ACKs** — atualiza `cwnd` conforme chegam
3. **Trata o resultado** — `ok`, `fast_retransmit` ou timeout

#### Os offsets

`base`, `off` e `last_ack_off` são todos índices dentro do array `data`:

```
data: [====confirmado====|----in flight----|...não enviado...]
                         ↑                ↑
                        base             off
               ↑
          last_ack_off  (avança com cada ACK)
```

- `base` — primeiro byte ainda não confirmado; onde a janela começa
- `off` — cursor de envio; avança enquanto `(off - base) < cwnd`
- `last_ack_off` — até onde o servidor já confirmou nesse RTT

A conversão entre offset e número de sequência TCP é:
```python
seq     = (isn + 1 + off) % MOD   # offset → seq
ack_off = (ack - (isn + 1)) % MOD # seq    → offset
```

### Controle de congestionamento

#### Slow Start
```python
cwnd += MSS
if cwnd >= ssthresh:
    mode = 'congestion_avoidance'
```

#### Congestion Avoidance
```python
cwnd += MSS * MSS / cwnd 
```

#### Detecção de perda — dois caminhos

**Timeout:** nenhum ACK chegou antes do `RTO`:
```python
ssthresh = max(cwnd / 2, 4 * MSS)
cwnd = MSS 
mode = 'slow_start'
```

**Fast Retransmit:** 3 ACKs duplicados chegaram:
```python
ssthresh = max(cwnd / 2, MSS)
cwnd = MSS
```

> O fast retransmit só funciona se houver pelo menos 3 pacotes depois do perdido na mesma janela.

### Four-way handshake

```
cliente  →  FIN (F=1)
servidor →  FIN-ACK (F=1, A=1)
```

## server.py

### Simulação de perda

```python
LOSS = 0.10  # 10% de chance de descartar um segmento
```

Quando um segmento é sorteado para perda, o servidor `drop_next = True` e para de avançar o `expected`. Os pacotes seguintes chegam fora de ordem e recebem ACK duplicado.

```python
if random.random() < LOSS:
    drop_next = True
    last_ack_sent = expected  # congela o ACK no seq perdido
    continue                  # não envia nada
```

### Tratamento de segmentos

| Situação | O que o servidor faz |
|---|---|
| `seq == expected` e sem perda pendente | Sorteia perda; se ok, envia ACK e avança `expected` |
| `seq == expected` e `drop_next=True` | Retransmissão feita |
| `seq != expected` e `drop_next=True` | Chegou fora de ordem, então envia ACK dup do segmento |
| `seq != expected` sem perda | Fora de ordem genérico (reenvia último ACK válido) |

---

## Como rodar

```bash
# terminal 1
python server.py

# terminal 2
python client.py
```

Ajuste `LOSS` em `server.py` conforme o desejado.