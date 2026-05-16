import socket, random   
from common import *             

LOSS = 0.05

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # AF_INET = IPv4 
sock.bind((HOST, PORT)) # associa o socket ao endereço e porta do server
print(f"Servidor em {HOST}:{PORT}  |  perda simulada = {LOSS*100:.0f}%\n")  

# three way handshake
while True: 
    raw, addr = sock.recvfrom(MAX_PKT) # recebe segmento e endereço do cliente
    p = unpack(raw)                                    
    if p and p['S'] and not p['A']: # verifica se é SYN (flag S=1, A=0) (common.py)
        client_isn = p['seq'] # armazena numero inicial de sequencia
        print(f"SYN recebido  seq={client_isn}")        
        break                                           

server_isn = random.randint(0, MOD - 1) # gera numero inicial de sequência
sock.sendto(pack(server_isn, client_isn + 1, 0, S=1, A=1), addr) # envia SYN-ACK
print(f"SYN-ACK enviado  seq={server_isn}")   

sock.settimeout(5)                                     
raw, _ = sock.recvfrom(MAX_PKT) # aguarda ACK final do cliente
print("ACK recebido — conexão estabelecida!\n")    

# ----------------------------------------------------------------------------------------

expected = (client_isn + 1) % MOD # proximo numero de sequência esperado
total = 0 # bytes recebidos
drop_next = False # indica que ha perda pendente (proximos segmentos sao ACK dup)
last_ack_sent = None # ultimo ACK enviado

sock.settimeout(10)                      
while True:                              
    try:
        raw, addr = sock.recvfrom(MAX_PKT)  # recebe segmento
    except socket.timeout:                  
        print("Timeout — encerrando.")      
        break                             

    p = unpack(raw)                 
           
    if not p:                             
        continue                        

    if p['F']: # verifica flag FIN
        print(f"\nFIN recebido. Total recebido: {total:,} bytes")
        sock.sendto(pack(server_isn + 1, (p['seq'] + 1) % MOD, 0, A=1, F=1), addr)  # envia FIN-ACK
        print("FIN-ACK enviado.") 
        break                          

    if p['seq'] == expected: # segmento chegou na ordem

        # se tinha perda pendente o segmento foi retransmitido
        if drop_next:
            drop_next = False
            total += p['dlen']  
            expected = (expected + p['dlen']) % MOD 
            last_ack_sent = expected  
            sock.sendto(pack(server_isn + 1, expected, 0, A=1), addr)  
            print(f"  [RETRANS OK] seq={p['seq']:5d} → ACK={expected}") 
            continue                                               

        # sorteia nova perda (não envia ACK nem avança expected)
        if random.random() < LOSS:
            drop_next = True                                  
            last_ack_sent = expected # o ultimo ack enviado é do segmento perdido (nao avanca)
            print(f"  [PERDA SIMULADA] seq={p['seq']:5d} — próximos pacotes gerarão ACK dup")
            continue

        next_ack = (expected + p['dlen']) % MOD # calcula próximo ACK esperado

        total += p['dlen']  

        # segmento ok (envia ACK normal e avança)
        expected = next_ack 
        last_ack_sent = next_ack 
        sock.sendto(pack(server_isn + 1, next_ack, 0, A=1), addr)  # envia ACK
        print(f"  seq={p['seq']}  dlen={p['dlen']}  → ACK={next_ack}") 

    else: # segmento fora de ordem ou retransmissão

        # cliente enviou pacotes posteriores a perda (gera ack dup)
        if drop_next:
            sock.sendto(pack(server_isn + 1, last_ack_sent, 0, A=1), addr)  # ACK dup do segmento perdido
            print(f"  [ACK DUP] seq={p['seq']:5d} → ACK={last_ack_sent}")
            
        elif p['seq'] == (expected - MSS) % MOD:   # duplicata do último aceito
            pass

        # sem perda so esta fora de ordem (generico)
        else:
            sock.sendto(pack(server_isn + 1, expected, 0, A=1), addr)  # reenvia ultimo ACK válido
            print(f"  Fora de ordem: esperado={expected} recebido={p['seq']}")