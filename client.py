import socket, os, time
from common import *             

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # AF_INET = IPv4
data = os.urandom(60 * 1024)  

# three way handshake
isn = __import__('random').randint(0, MOD - 1)  # numero de sequência inicial

sock.sendto(pack(isn, 0, 0, S=1), (HOST, PORT))  # envia SYN
print(f"SYN enviado  seq={isn}")               

sock.settimeout(RTO)                           
raw, _ = sock.recvfrom(MAX_PKT)                 # recebe SYN-ACK
p = unpack(raw)                                 
server_isn = p['seq']                           # armazena ISN do servidor
print(f"SYN-ACK recebido  seq={server_isn}")  

sock.sendto(pack(isn + 1, server_isn + 1, 0, A=1), (HOST, PORT))  # envia ACK final
print("ACK enviado — conexão estabelecida!\n") 

# ----------------------------------------------------------------------------------------

cwnd = float(CWND0)     
ssthresh = float(SSTHRESH0)    
mode = 'slow_start'        
base = 0                   
total = len(data)          
retrans = 0                   
t0 = time.time()         

while base < total: 
    # Monta e envia janela
    pkts, off = [], base     
    # data = [byte0, byte1, ..., byte61439]

    # cada iteracao verifica se pode enviar mais um segmento
    while off < total and (off - base) < int(cwnd):
        chunk = data[off: off + MSS]
        seq = (isn + 1 + off) % MOD # calcula número de sequência
        sock.sendto(pack(seq, 0, len(chunk), chunk), (HOST, PORT))  # envia segmento

        print(f"  → DATA seq={seq:5d} len={len(chunk)}")

        pkts.append((seq, off, len(chunk)))    
        off += len(chunk) # avança offset

    expected_ack = (isn + 1 + off) % MOD # ACK esperado apos envio da janela
    last_ack_off = base # ultimo offset confirmado por ACK

    sock.settimeout(RTO)                       
    ok = False                      
    dup_acks = 1 # contador de ACKs duplicados
    last_ack = None # ultimo valor de ACK recebido
    fast_retransmit = False

    try:
        while True:
            p = unpack(sock.recvfrom(MAX_PKT)[0])                  

            if not p or not p['A']:           
                continue

            print(f"  ← ACK={p['ack']:5d}")

            # ack duplicado
            if p['ack'] == last_ack:
                dup_acks += 1                 

                if dup_acks == 3:
                    print(f"  [3 ACKs DUP] → Fast Retransmit")
                    ssthresh = max(cwnd / 2, float(MSS))
                    cwnd = float(MSS)
                    mode = 'slow_start'

                    # Retransmite o seq perdido
                    seq_perdido = p['ack']
                    off_perdido = (seq_perdido - (isn + 1)) % MOD
                    chunk = data[off_perdido: off_perdido + MSS]
                    sock.sendto(pack(seq_perdido, 0, len(chunk), chunk), (HOST, PORT))
                    print(f"  → RETRANS seq={seq_perdido:5d}")
                    dup_acks = 0
                    fast_retransmit = True
                    break                               

                continue # ACK dup mas ainda < 3

            dup_acks = 1                                  
            last_ack = p['ack']                           

            ack_off = (p['ack'] - (isn + 1)) % MOD # converte ACK para offset nos dados
            if ack_off <= last_ack_off:                  
                continue

            last_ack_off = ack_off # atualiza último offset confirmado

            if mode == 'slow_start':                      
                cwnd += MSS # crescimento exponencial (+1 MSS por ACK)
                if cwnd >= ssthresh:                     
                    mode = 'congestion_avoidance'
            else:
                cwnd += MSS * MSS / cwnd # crescimento linear (+1 MSS por RTT)

            if p['ack'] == expected_ack:
                ok = True 
                base = off # avança base para próxima janela
                break 

    except socket.timeout:
        pass  # timeout tratado abaixo

    # ultimo ACK confirmado antes de tratar timeout
    if last_ack_off > base:  
        # Marca onde a próxima janela começa                         
        base = last_ack_off                           

    n = len(pkts) # numero de segmentos enviados
    if ok:
        print(f"RTT: {n}  CWND: {cwnd/MSS}  MODO: {mode}")
    elif fast_retransmit:
        print(f"RTT: {n}  CWND: {cwnd/MSS}  MODO: {mode}  FAST RETRANSMIT")
        base = last_ack_off
    else:
        # Timeout nenhum ACK recebido
        retrans  += 1                                 
        ssthresh = max(cwnd / 2, float(4 * MSS))   
        cwnd = float(MSS)                        
        mode = 'slow_start'                     
        print(f"RTT: {n}  CWND: {cwnd/MSS}  MODO: {mode}  TIMEOUT #{retrans}") 

# four way handshake
sock.sendto(pack((isn + 1 + total) % MOD, 0, 0, F=1), (HOST, PORT)) # envia FIN
print("\nFIN enviado. Aguardando FIN-ACK...")  
try:
    sock.settimeout(2)                        
    sock.recvfrom(MAX_PKT) # aguarda FIN-ACK
    print("FIN-ACK recebido — conexão encerrada.") 
except socket.timeout:
    pass                                     

elapsed = time.time() - t0                    
print(f"\nTotal: {total:,} B  |  Tempo: {elapsed:.2f}s")