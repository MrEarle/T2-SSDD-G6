import logging
import socket
import threading
from datetime import time

import socketio
from colorama import Fore as Color
from werkzeug.serving import run_simple

from .gui_socketio import GUI
from ..utils.vectorClock import VectorClock
from ..utils.networking import get_public_ip

logger = logging.getLogger(f"{Color.CYAN}[Server]{Color.RESET}")


def dns_lookup(addr: str):
    return "http://localhost:3001"


class P2P:
    def __init__(self) -> None:
        self.p2p_srv = socketio.Server(cors_allowed_origin="*")
        self.app = socketio.WSGIApp(self.p2p_srv)

        self.gui: GUI = None
        self.clock: VectorClock = None

    def initialize_p2p_server(self, gui):
        self.gui = gui
        self.p2p_srv.on("connect", self.on_p2p_connect)

    def on_p2p_connect(self, sid, environ, auth: dict):
        auth["username"] = f"{auth['username']} → {self.gui.name}"
        self.clock.receive_message(auth)

    def __start(self, public_ip: str = "localhost", port: int = 3000):
        logger.debug("Starting p2p server")
        run_simple(public_ip, port, self.app)

    def start(self) -> int:
        public_ip, port = get_public_ip()
        logger.debug(f"P2P server adress {public_ip}:{port}")

        threading.Thread(target=self.__start, args=[public_ip, port]).start()

        return public_ip, port

    def send_private_message(
        self, uri: str, from_user: str, to_user: str, to_user_id: str, message: str
    ):
        while self.clock is None:
            time.sleep(0.01)
        client = socketio.Client()
        msg = self.clock.send_message(message, to_user_id)
        msg["username"] = from_user

        client.connect(uri, auth=msg)

        client.disconnect()

        self.gui.addMessage(f"<{from_user} → {to_user}> {message}")
