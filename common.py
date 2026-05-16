import struct

MSS = 1024    # bytes por segmento
HDR = 8       # bytes do header
MAX_PKT = 1032    # MSS + HDR
CWND0 = MSS     # janela inicial
SSTHRESH0 = 15360   # 15 * MSS
RTO = 0.5     # timeout em segundos
# numero de 0 a 65535
MOD = 65536
RECV_BUFFER = 32 * MSS

HOST, PORT = '127.0.0.1', 5000

# monta o segmento
def pack(seq, ack, dlen, data=b'', wnd=RECV_BUFFER, A=0, S=0, F=0):

    # junta tamanho + flags em 2 bytes
    flags = (dlen << 3) | (A << 2) | (S << 1) | F

    return struct.pack(
        '!HHHH',
        seq % MOD,     
        ack % MOD,     
        wnd,           
        flags           
    ) + data


# descompacta o segmento
def unpack(raw):

    # pacote menor que header
    if len(raw) < HDR:
        return None

    # le header
    seq, ack, wnd, flags = struct.unpack('!HHHH', raw[:HDR])

    # separa os bits
    dlen = (flags >> 3) & 0x1FFF
    A = (flags >> 2) & 1
    S = (flags >> 1) & 1
    F = flags & 1

    return {
        'seq': seq,
        'ack': ack,
        'wnd': wnd,
        'dlen': dlen,
        'A': A,
        'S': S,
        'F': F,
        'payload': raw[HDR:]
    }