import logging
from threading import Thread
from time import sleep

from colorama import Fore as Color
from .Server import Server

logger = logging.getLogger(f"{Color.MAGENTA}[MigrationManager]{Color.RESET}")


class MigrationManager:
    def __init__(self, port: int = 3000, min_n: int = 0) -> None:
        self.server: Server = None
        self.server_th: Thread = None
        self.port = port
        self.min_n = min_n

    def _start_server(self):
        self.server = Server(self.port, self.min_n)
        self.server.serve()

    def _migrate(self):
        # TODO: Manejar logica de migracion

        # Migracion debe finalizar terminando el server
        logger.debug("Terminating server")
        self.server.stop()
        self.server_th.join()

    def _start_server_cycle(self):
        logger.debug("Starting server cycle")
        self.server_th = Thread(target=self._start_server, daemon=True)

        logger.debug("Starting server")
        self.server_th.start()

        logger.debug("Waiting for cycle to end (30s)")
        sleep(30)

        logger.debug("Cycle ended, initializing migration")
        self._migrate()

    def start(self):
        self._start_server_cycle()
