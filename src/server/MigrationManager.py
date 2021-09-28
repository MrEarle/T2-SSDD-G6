import logging
from threading import Thread
from time import sleep

from colorama import Fore as Color
from .Server import Server
from ..utils.networking import get_public_ip, send_server_addr

logger = logging.getLogger(f"{Color.MAGENTA}[MigrationManager]{Color.RESET}")


class MigrationManager:
    def __init__(
        self,
        dns_host: str,
        dns_port: int,
        server_uri: str,
        port: int = 3000,
        min_n: int = 0,
    ) -> None:
        self.server: Server = None
        self.server_th: Thread = None
        self.port = port
        self.min_n = min_n
        self.dns_host = dns_host
        self.dns_port = dns_port
        self.server_uri = server_uri

    def _start_server(self):
        self.server = Server(self.ip, self.port, self.min_n)
        self.server.serve()

    def _migrate(self):
        # TODO: Manejar logica de migracion

        # Avisar a clientes que paren de mandar mensajes
        self.server.send_pause_messaging_signal(pause=True)
        # Por ahora solo pausar el servicio por 10 segundos
        self.server.server.sleep(10)
        self.server.send_pause_messaging_signal(pause=False)
        return
        # TODO: Elegir nuevo servidor y comunicar migración

        # Una vez que el nuevo server responda con su inicializacion del server:
        # TODO: Mandar vector clock
        # TODO: Mandar lista de usuario

        # Una vez que se hayan migrado los datos:
        # TODO: Comunicar a clientes que reconecten

        # Migracion debe finalizar terminando el server
        logger.debug("Terminating server")
        self.server.stop()
        self.server_th.join()

    def _start_server_cycle(self):
        logger.debug("Starting server cycle")
        # Iniciar el servidor en otro thread
        self.ip, port = get_public_ip()
        self.port = self.port or port
        send_server_addr(
            self.dns_host,
            self.dns_port,
            self.server_uri,
            f"http://{self.ip}:{self.port}",
        )
        self.server_th = Thread(target=self._start_server, daemon=True)

        logger.debug("Starting server")
        self.server_th.start()
        self.server_th.join()

        logger.debug("Waiting for cycle to end (30s)")
        # 30 segundos para migrar
        sleep(30)

        logger.debug("Cycle ended, initializing migration")
        # Migrar
        self._migrate()

        # TODO: Temporal. Es mientras no se implementa completamente la migración
        while True:
            self.server.server.sleep(10)

    def start(self):
        self._start_server_cycle()