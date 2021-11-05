import logging
import pickle as pkl
from threading import Thread
from time import sleep
from typing import Callable

import socketio
from colorama import Fore as Color
from .Server import Server
from ..utils.networking import (
    get_public_ip,
    request_random_server,
    request_replica_addr,
    send_server_addr,
    change_server_addr,
)

logger = logging.getLogger(f"{Color.MAGENTA}[MigrationManager]{Color.RESET}")


class MigrationManager:
    def __init__(
        self,
        dns_host: str,
        dns_port: int,
        server_uri: str,
        min_n: int = 0,
    ) -> None:
        self.server: Server = None
        self.server_th: Thread = None
        self.port: int = None
        self.min_n = min_n
        self.dns_host = dns_host
        self.dns_port = dns_port
        self.server_uri = server_uri

    def _start_server(self):
        self.server = Server(
            self,
            self.ip,
            self.port,
            self.min_n,
        )
        self.server.serve()

    def get_replica_address(self):
        return request_replica_addr(
            self.dns_host,
            self.dns_port,
            self.addr,
            self.server_uri,
        )

    def _migrate(self):
        # TODO: 1. Request random server
        selected_server = False
        new_addr = None
        while not selected_server or new_addr == None:
            new_addr = request_random_server(self.dns_host, self.dns_port, self.server_uri)
            print(new_addr, "_migrate")

            if not new_addr:
                return False

            # TODO: 2. Conectar y notificar migracion
            logger.debug(f"Selected new server {new_addr}")
            # TODO: Implementar bien esta funcion + OK
            selected_server = self.request_migration_connection(new_addr)

        # TODO: 4. Pausar clientes
        # Avisar a clientes que paren de mandar mensajes
        self.server.send_pause_messaging_signal(pause=True)

        # TODO: 5. Mandar data a nuevo server
        messages = self.server.messages
        self.request_migration(messages, self._on_migrate_complete, new_addr)
        return True

        # Una vez que el nuevo server responda con su inicializacion del server:

    def request_migration_connection(self, addr: str):
        try:
            self.client = socketio.Client()
            self.client.connect(
                addr,
                auth={
                    "migration": True,
                },
            )
            return self.client.connected
        except Exception as e:
            logger.error(e)
            return False

    def request_migration(self, messages, callback: Callable, addr):
        messages = messages
        data = (messages, self.server.min_user_count, self.server.history_sent)

        def on_ack():
            self.client.disconnect()
            self.client = None
            callback(addr)
            self.server.cleanup()

        self.client.emit("migrate", data, callback=on_ack)

    def _on_migrate_complete(self, addr):
        # Una vez que se haya migrado los datos:
        # Comunicar para que se reconecten
        logger.debug("Sending reconnection signals")
        change_server_addr(
            self.dns_host,
            self.dns_port,
            self.server_uri,
            server_addr=addr,
            self_addr=self.addr,
            callback=self.server.send_reconnect_signal,
        )
        return True

    def _start_server_cycle(self):
        logger.debug("Starting server cycle")
        # Iniciar el servidor en otro thread
        self.ip, self.port = get_public_ip()
        self.addr = f"http://{self.ip}:{self.port}"
        _, is_active_server = send_server_addr(
            self.dns_host,
            self.dns_port,
            self.server_uri,
            self.addr,
        )

        self.server_th = Thread(target=self._start_server, daemon=True)

        logger.debug("Starting server")
        self.server_th.start()

        self.cycle_th = Thread(target=self._server_cycle, daemon=True)
        if is_active_server:
            self.cycle_th.start()

    def start(self):
        self._start_server_cycle()

    def _server_cycle(self):
        """
        Metodo para correr el ciclo en un nuevo servidor
        """
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
