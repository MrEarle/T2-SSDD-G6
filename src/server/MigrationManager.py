import logging
from src.server.MigrationServer import MigrationServer
from threading import Thread
from time import sleep

from colorama import Fore as Color
from .Server import Server
from ..utils.networking import get_public_ip, request_random_server, send_server_addr

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

    def _start_server(self, vector_clock_init=None, messages=None):
        self.server = Server(
            self.ip,
            self.port,
            self.min_n,
        )
        self.server.serve()

    def _migrate(self):
        # TODO: 1. Request random server
        selected_server = False
        while not selected_server:
            new_addr = request_random_server(
                self.dns_host, self.dns_port, self.migration_server.server_uri
            )
            if new_addr is None:
                self.server.send_pause_messaging_signal(pause=False)
                return False

            # TODO: 2. Conectar y notificar migracion
            logger.debug(f"Selected new server {new_addr}")


            # TODO: Implementar bien esta funcion
            selected_server = self.migration_server.request_migration_connection(
                new_addr
            )

        # TODO: 3. Esperar a OK del nuevo server

        # TODO: 4. Pausar clientes
        # Avisar a clientes que paren de mandar mensajes
        self.server.send_pause_messaging_signal(pause=True)

        # TODO: 5. Mandar data a nuevo server

        # TODO: 6. Esperar ok de nuevo server y cambiar flag de server

        # TODO: 7. Mandar mensaje de reconexion

        # Una vez que el nuevo server responda con su inicializacion del server:
        vector_clock_inits = self.server.clock.dump()
        messages = self.server.messages
        # Elegir nuevo servidor y comunicar migración
        selected_server = False
        while not selected_server:
            new_addr = request_random_server(
                self.dns_host, self.dns_port, self.migration_server.server_uri
            )
            if new_addr is None:
                self.server.send_pause_messaging_signal(pause=False)
                return False

            logger.debug(f"Selected new server {new_addr}")
            selected_server = self.migration_server.request_migration_connection(
                new_addr
            )

        # Mandar vector clock
        # Mandar lista de usuario
        self.migration_server.request_migration(
            vector_clock_inits, messages, self._on_migrate_complete
        )

    def _on_migrate_complete(self):
        # Una vez que se haya migrado los datos:
        # Comunicar para que se reconecten
        logger.debug("Sending reconnection signals")
        self.server.send_reconnect_signal()

        # Migracion debe finalizar terminando el server
        logger.debug("Terminating server")
        self.server.stop()
        return True

    def _start_server_cycle(
        self, start_as_server=False, vectorClock=None, messages=None
    ):
        logger.debug("Starting server cycle")
        # Iniciar el servidor en otro thread
        self.ip, self.port = get_public_ip()
        send_server_addr(
            self.dns_host,
            self.dns_port,
            self.server_uri,
            f"http://{self.ip}:{self.port}",
        )

        if not start_as_server:
            return

        self.server_th = Thread(
            target=self._start_server, args=[vectorClock, messages], daemon=True
        )

        logger.debug("Starting server")
        self.server_th.start()

        while True:
            logger.debug("Waiting for cycle to end (30s)")
            # 30 segundos para migrar
            sleep(30)

            logger.debug("Cycle ended, initializing migration")
            # Migrar
            migration_success = self._migrate()
            if migration_success:
                logger.debug("Migration success")
                break
            else:
                logger.debug("Migration failed, repeating cycle")

    def start(self, start_as_server=False):
        self._start_server_cycle(start_as_server=start_as_server)
