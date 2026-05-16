import socket, os, time, csv
from common import *             

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # AF_INET = IPv4 SOCK_DGRAM = UDP
# len = 61440 
data = os.urandom(60 * 1024)  

# three way handshake
isn = __import__('random').randint(0, MOD - 1) # numero de sequência inicial

sock.sendto(pack(isn, 0, 0, S=1), (HOST, PORT)) # envia SYN
print(f"SYN enviado  seq={isn}")               

sock.settimeout(RTO)                           
raw, _ = sock.recvfrom(MAX_PKT) # recebe SYN-ACK
p = unpack(raw)                                 
server_isn = p['seq'] # armazena ISN do servidor
print(f"SYN-ACK recebido  seq={server_isn}")  

sock.sendto(pack(isn + 1, server_isn + 1, 0, A=1), (HOST, PORT))  # envia ACK final
print("ACK enviado — conexão estabelecida!\n") 

# ----------------------------------------------------------------------------------------

# window size do servidor
rwnd = p['wnd']

sock.setblocking(False)

cwnd = float(CWND0)     
ssthresh = float(SSTHRESH0)    
mode = 'slow_start'        
base = 0                   
total = len(data)          
retrans = 0         
timeouts = 0          
t0 = time.time()      

csv_file = open('congestion.csv', 'w', newline='')
writer   = csv.writer(csv_file)
writer.writerow(['tempo', 'cwnd', 'ssthresh', 'modo', 'evento'])

while base < total: 
    sent = 0

    while base + sent < total and sent < int(cwnd) and sent < int(rwnd):
        chunk = data[base + sent : base + sent + MSS]
        seq = (isn + 1 + base + sent) % MOD
        sock.sendto(pack(seq, 0, len(chunk), chunk), (HOST, PORT))
        print(f"  → DATA seq={seq:5d} len={len(chunk)}")
        sent += len(chunk)

    expected_ack = (isn + 1 + base + sent) % MOD

    ok = False                      
    dup_acks = 1
    last_ack = None # ultimo valor de ACK recebido
    fast_retransmit = False
    confirmed = 0 # bytes confirmados neste burst
    t_start = time.time()

    cwnd_send = cwnd
    ssthresh_send = ssthresh
    mode_send = mode

    while True:
        if time.time() - t_start > RTO:  # RTO expirou
            break

        try:
            raw, _ = sock.recvfrom(MAX_PKT)
        except BlockingIOError:
            continue                

        p = unpack(raw)
        
        if not p or not p['A']:           
            continue

        rwnd = p['wnd']

        print(f"  ← ACK={p['ack']:5d}")

        # ack duplicado
        if p['ack'] == last_ack:
            dup_acks += 1                 

            if dup_acks == 3:
                print(f"  [3 ACKs DUP] → Fast Retransmit")

                if mode != 'fast_recovery':  # só calcula na primeira vez
                    ssthresh = max(cwnd / 2, float(4 * MSS))
                    cwnd = ssthresh + 3 * MSS
                    mode = 'fast_recovery'

                seq_perdido = p['ack']
                off_perdido = (seq_perdido - (isn + 1)) % MOD
                chunk = data[off_perdido: off_perdido + MSS]
                sock.sendto(pack(seq_perdido, 0, len(chunk), chunk), (HOST, PORT))
                print(f"  → RETRANS seq={seq_perdido:5d}")
                dup_acks = 0
                fast_retransmit = True
                t_start = time.time()
                continue

            continue

        dup_acks = 1
        last_ack = p['ack']

        ack_bytes = (p['ack'] - (isn + 1)) % MOD
        new_confirmed = ack_bytes - base

        if new_confirmed <= confirmed:
            continue

        confirmed = new_confirmed

        if mode == 'fast_recovery':           
            cwnd = ssthresh                   
            mode = 'congestion_avoidance'
            writer.writerow([f'{time.time()-t0:.4f}', f'{cwnd/MSS:.4f}', f'{ssthresh/MSS:.4f}', mode, 'fast_recovery'])
            break

        elif mode == 'slow_start':
            cwnd += MSS
            writer.writerow([f'{time.time()-t0:.4f}', f'{cwnd/MSS:.4f}', f'{ssthresh/MSS:.4f}', mode, 'ok'])
            if cwnd >= ssthresh:
                mode = 'congestion_avoidance'

        elif mode == 'congestion_avoidance':
            cwnd += MSS * MSS / cwnd
            writer.writerow([f'{time.time()-t0:.4f}', f'{cwnd/MSS:.4f}', f'{ssthresh/MSS:.4f}', mode, 'ok'])

        if p['ack'] == expected_ack:
            ok = True
            break

    n = sent // MSS

    if ok:
        print(f"RTT: {n}  CWND: {cwnd_send/MSS:.2f}  SSTHRESH: {ssthresh_send/MSS:.2f}  MODO: {mode_send}\n")
        base += sent
    elif fast_retransmit:
        retrans += 1
        print(f"RTT: {n}  CWND: {cwnd_send/MSS:.2f}  SSTHRESH: {ssthresh_send/MSS:.2f}  MODO: {mode_send}  FAST RECOVERY #{retrans}\n")
        base += confirmed 
    else:
        timeouts += 1
        ssthresh = max(cwnd / 2, float(4 * MSS))
        cwnd = float(MSS)
        mode = 'slow_start'
        base += confirmed
        writer.writerow([f'{time.time()-t0:.4f}', f'{cwnd/MSS:.4f}', f'{ssthresh/MSS:.4f}', mode, 'timeout'])
        print(f"RTT: {n}  CWND: {cwnd_send/MSS:.2f}  SSTHRESH: {ssthresh_send/MSS:.2f}  MODO: {mode_send}  TIMEOUT #{timeouts}\n")

csv_file.close()

# four way handshake
sock.setblocking(True)
sock.sendto(pack((isn + 1 + total) % MOD, 0, 0, F=1), (HOST, PORT)) # envia FIN
print("\nFIN enviado. Aguardando FIN-ACK...")  
try:
    sock.settimeout(2)                        
    sock.recvfrom(MAX_PKT) # aguarda FIN-ACK
    print("FIN-ACK recebido — conexão encerrada.") 
except socket.timeout:
    pass                                     

elapsed = time.time() - t0                    
print(f"\nTotal: {total:,} B  |  Tempo: {elapsed:.2f}s |  Taxa: {total/elapsed/1024:.2f} KB/s  |  Retransmissões: {retrans} |  Timeouts: {timeouts}")