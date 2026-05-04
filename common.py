import struct

MSS = 1024 # bytes por segmento
HDR = 8 # bytes do header
MAX_PKT = 1032 # MSS + HDR
CWND0 = MSS
SSTHRESH0 = 15360
RTO = 0.5 
# com o MOD = 65536 os numeros de sequencia são 16 bits e vão de 0 a 65535
# quando passam de 65535 voltam ao zero
MOD = 65536

HOST, PORT = '127.0.0.1', 5000

# monta segmento header + dados
def pack(seq, ack, dlen, data=b'', A=0, S=0, F=0):
    """Monta pacote: header (8 bytes) + dados."""
    flags = (dlen << 3) | (A << 2) | (S << 1) | F
    return struct.pack('!HHHH', seq % MOD, ack % MOD, 0, flags) + data
    # struct.pack('!HHHBBB', seq, ack, dlen, A, S, F)

# decodifica segmento recebido com um dict do header e o payload
def unpack(raw):
    if len(raw) < HDR:
        return None
    seq, ack, _, flags = struct.unpack('!HHHH', raw[:HDR])
    return {
        'seq': seq, 'ack': ack,
        'dlen': (flags >> 3) & 0x1FFF,
        'A': (flags >> 2) & 1,
        'S': (flags >> 1) & 1,
        'F':  flags        & 1,
        'payload': raw[HDR:]
    }