import logging
from src.utils.vectorClock import VectorClock
from typing import Callable, List, Tuple
from src.utils.networking import get_public_ip, send_server_addr
import socketio
from colorama import Fore as Color
from werkzeug.serving import make_server
from threading import Thread

logger = logging.getLogger(f"{Color.RED}[MgrationServer]{Color.RESET}")


class MigrationServer:
    def __init__(
        self,
        dns_host: str,
        dns_port: int,
        on_start_server: Callable[[bool, VectorClock, list], None],
    ) -> None:
        self.dns_host = dns_host
        self.dns_port = dns_port
        self.on_start_server = on_start_server

        self.server = socketio.Server(cors_allowed_origins="*")
        self.app = socketio.WSGIApp(self.server)

        self.host, self.port = get_public_ip()
        self.server_uri = f"migration@{self.host}:{self.port}"

        send_server_addr(
            self.dns_host,
            self.dns_port,
            self.server_uri,
            f"http://{self.host}:{self.port}",
        )

        self.__created_server = make_server(
            self.host,
            self.port,
            self.app,
            threaded=True,
        )

        self.setup()

    def serve(self):
        logger.debug(f"Running App on http://{self.host}:{self.port}")
        self.__created_server_th = Thread(
            target=self.__created_server.serve_forever, daemon=True
        )
        self.__created_server_th.start()

    def setup(self):
        self.server.on("migrate", self.on_migrate)

    def on_migrate(self, sid: str, data: dict):
        vector_clock_init_vals: Tuple[dict, dict] = data["VECTOR_CLOCK"]
        messages: List[Tuple[str, str]] = data["MESSAGES"]

        self.on_start_server(True, vector_clock_init_vals, messages)

        return True

    def request_migration_connection(self, addr: str):
        try:
            self.client = socketio.Client()
            self.client.connect(addr)
            return self.client.connected
        except Exception as e:
            logger.error(e)
            return False

    def request_migration(self, vector_clock_inits, messages, callback: Callable):
        msg = {"VECTOR_CLOCK": vector_clock_inits, "MESSAGES": messages}

        def on_ack():
            self.client.disconnect()
            self.client = None
            callback()

        self.client.emit("migrate", msg, callback=on_ack)
