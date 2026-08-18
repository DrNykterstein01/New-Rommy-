import socket
import threading
import json
import logging
import time

# pyrefly: ignore [missing-import]
from .state import NetworkState
# pyrefly: ignore [missing-import]
from .config import NetworkConfig

logger = logging.getLogger(__name__)

class Discovery:
    """Servicio de descubrimiento UDP (Broadcast) para redes locales."""
    
    def __init__(self, state: NetworkState, config: NetworkConfig = None):
        self.state = state
        self.config = config or NetworkConfig()
        self.discovered_servers = []
        self._servers_lock = threading.Lock()
    
    def start_broadcast(self):
        """Inicia el broadcast periódico de la sala (SOLO HOST, CORRE EN HILO)."""
        def broadcast_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            while self.state.running_broadcast:
                try:
                    # Determinar IP local del HOST para publicarla
                    local_ip = "127.0.0.1"
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(('10.255.255.255', 1))
                        local_ip = s.getsockname()[0]
                        s.close()
                    except Exception:
                        pass
                    
                    server_data = {
                        "name": self.state.gameName or "Sala de Rummy 500",
                        "playerName": self.state.playerName or "Host",
                        "ip": local_ip,
                        # El puerto REAL de esta sala (asignado dinámicamente
                        # por el SO en server.py), no el fijo de config: con
                        # el puerto fijo, dos salas en la misma máquina
                        # anunciaban el mismo puerto y un cliente terminaba
                        # conectándose siempre a la primera que lo ocupó,
                        # sin importar cuál hubiera elegido en realidad.
                        "port": self.state.port or self.config.TCP_PORT,
                        "max_players": self.state.max_players or 4,
                        "currentPlayers": len(self.state.get_connected_players()),
                    }
                    
                    packet = json.dumps(server_data).encode('utf-8')
                    # Broadcastear al puerto definido
                    sock.sendto(packet, ('<broadcast>', self.config.BROADCAST_PORT))
                    logger.debug(f"Broadcast enviado UDP: Sala '{server_data['name']}' IP {server_data['ip']}")
                    
                    time.sleep(self.config.BROADCAST_INTERVAL)
                except Exception as e:
                    logger.error(f"Error en broadcast UDP: {e}")
                    time.sleep(1) # Prevenir bucle de alto consumo en caso de error
            
            sock.close()
        
        self.state.running_broadcast = True
        threading.Thread(target=broadcast_loop, daemon=True).start()
    
    def discover_servers(self, timeout: int = 5):
        """Escucha paquetes UDP broadcast y actualiza discovered_servers asincronamente."""
        with self._servers_lock:
            self.discovered_servers = []
        
        def listen_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Escuchar en cualquier interfaz sobre el puerto de broadcast
            try:
                sock.bind(('', self.config.BROADCAST_PORT))
            except Exception as e:
                logger.error(f"Error bindeando socket UDP de escucha: {e}")
                return
                
            sock.settimeout(1)
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    server_dict = json.loads(data.decode('utf-8'))

                    if not isinstance(server_dict, dict):
                        continue

                    # La IP de origen evita que varios anuncios con una IP
                    # publicada como 127.0.0.1 se consideren la misma sala.
                    server_dict["ip"] = addr[0]
                    # OJO: NO usar server_dict.get("port") para la clave de
                    # deduplicación. Ese campo es el TCP_PORT fijo que todo
                    # servidor anuncia igual (network/config.py), así que dos
                    # salas reales en la MISMA máquina (misma IP de origen,
                    # mismo TCP_PORT anunciado) terminaban con la misma
                    # clave y una tapaba a la otra. En cambio, `addr` (el
                    # origen real del paquete UDP) sí es único por servidor:
                    # cada broadcast_loop() crea y reutiliza su propio socket
                    # para todos sus envíos, así que el puerto de origen
                    # efímero (addr[1]) se mantiene estable para ESE servidor
                    # y es distinto al de cualquier otro, incluso corriendo
                    # en la misma computadora. Se guarda junto con la entrada
                    # (server_dict["_source_addr"]) para poder reconocer los
                    # próximos paquetes de este mismo servidor y no tratarlos
                    # como una sala nueva cada vez que vuelve a anunciarse.
                    server_dict["_source_addr"] = list(addr)
                    server_key = addr
                    with self._servers_lock:
                        indice_existente = next(
                            (i for i, server in enumerate(self.discovered_servers)
                             if tuple(server.get("_source_addr", ())) == server_key),
                            None
                        )
                        if indice_existente is None:
                            self.discovered_servers.append(server_dict)
                            logger.info(f"Sala descubierta en LAN: {server_dict.get('name', '?')} en {server_dict.get('ip', '?')}")
                        else:
                            # Ya la conocíamos: refresca sus datos (p. ej.
                            # currentPlayers puede haber cambiado) en vez de
                            # agregarla de nuevo como si fuera otra sala.
                            self.discovered_servers[indice_existente] = server_dict
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error al decodificar paquete de descubrimiento: {e}")
            
            sock.close()
        
        listen_thread = threading.Thread(target=listen_loop, daemon=True)
        listen_thread.start()
        # No hacemos join() para no bloquear la interfaz.