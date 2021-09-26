import logging
import socketio
import eventlet
from eventlet import wsgi
from colorama import Fore as Color
from .ServerNoNamespace import Server

logger = logging.getLogger(f"{Color.BLUE}[MigrationManager]{Color.RESET}")
logger.setLevel(logging.DEBUG)


class MigrationManager:
    def __init__(self, min_user_count: int = 0, port: int = 3000) -> None:
        self.min_user_count = min_user_count

        self.port = port

        self.server = socketio.Server(
            logger=True,
            cors_allowed_origins="*",
            engineio_logger=True,
            async_mode="eventlet",
        )
        self.app = socketio.WSGIApp(self.server)

        self.setup()

    def setup(self):
        logger.debug("Setting up namespaces")
        self.server_namespace = Server(self.server, self.min_user_count)
        self.server_namespace.setup_handlers()
        # TODO: Manejar namespace /chat
        # self.server.register_namespace(self.server_namespace)
        # TODO: Manejar namespace /migration
        logger.debug("DONE: Setting up namespaces")

    def serve(self):
        print("JPASDFASDFASDFA")
        logger.debug(f"Running App on port {self.port}")
        wsgi.server(eventlet.listen(("localhost", self.port)), self.app)
        logger.debug("Server disconnected")
