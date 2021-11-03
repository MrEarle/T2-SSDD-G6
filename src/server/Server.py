import logging
import pickle as pkl
from threading import Thread
from typing import TypedDict

import socketio
from colorama import Fore as Color
from werkzeug.serving import make_server

from .ServerCoordinator import ServerCoordinator

from ..utils.vectorClock import MESSAGE, SENDER_ID, VectorClock

from .Users import UserList

logger = logging.getLogger(f"{Color.GREEN}[Server]{Color.RESET}")
authType = TypedDict("Auth", {"username": str, "publicUri": str})


class Server:
    def __init__(
        self,
        migration_manager,
        host: str,
        port: int = 3000,
        min_user_count: int = 0,
    ) -> None:
        self.server = socketio.Server(cors_allowed_origins="*")
        self.app = socketio.WSGIApp(self.server)
        self.migration_manager = migration_manager
        self.port = port
        self.host = host

        self.__created_server = make_server(
            host,
            port,
            self.app,
            threaded=True,
        )
        self.__created_server_th: Thread = None
        self.__migrating = False

        self.users = UserList()
        self.history_sent = False
        self.min_user_count = min_user_count
        self.messages = {}

        self.server_coord = ServerCoordinator(self.server, self)
        self.next_index = 0

        self.setup_handlers()

        self.clock: VectorClock = VectorClock("server", self._on_clock_deliver_message)

    def setup_handlers(self):
        self.server.on("connect", self.on_connect)
        self.server.on("disconnect", self.on_disconnect)
        self.server.on("chat", self.on_chat)
        self.server.on("addr_request", self.addr_request)
        self.server.on("migrate", self.on_migrate)
        self.server.on("*", self.catch_all)

    def serve(self):
        # TODO: Registrarse en el DNS
        logger.debug(f"Running App on http://{self.host}:{self.port}")
        self.__created_server_th = Thread(target=self.__created_server.serve_forever, daemon=True)
        self.__created_server_th.start()

    def stop(self):
        self.__created_server.shutdown()
        self.__created_server_th.join()
        logger.debug("Server terminated")

    def on_connect(self, sid: str, environ: dict, auth: authType):
        """
        On connect, create a new user
        Parameters:
            auth: { username: str, publicId: str }
        """
        # Manejar conexion de migracion
        if "migration" in auth:
            self.on_connect_migration(sid, auth)

        # Manejar conexion de cliente
        else:
            self.on_connect_client(sid, auth)

    def on_connect_migration(self, sid: str, auth: authType):
        # TODO: Si en auth hay un flag de migracion, hacer logica de migracion
        print(auth)
        pass

    def on_connect_client(self, sid: str, auth: authType):
        # Si estoy migrando no aceptar conexiones de clientes
        if self.__migrating:
            raise ConnectionRefusedError()

        logger.debug(f"User logging in with auth: {auth}")
        user = self.users.add_user(auth["username"], sid, auth["publicUri"])

        if user is None:
            logger.debug(f'Username {auth["username"]} is already taken')
            raise ConnectionRefusedError("Username is invalid or already taken")

        if not auth["reconnecting"]:
            self.server.emit(
                "server_message",
                {"message": f'\u2713 {auth["username"]} has connected to the server'},
            )

        self.server.emit("send_uuid", user.uuid, room=sid)

        # Si se supero el limite inferior de usuarios conectados, mandar la historia
        if len(self.users) >= self.min_user_count and not auth["reconnecting"]:
            logger.debug(f"Sending history")

            if self.history_sent:
                # Solo al cliente conectado si ya se mando a todos
                self.server.emit(
                    "message_history",
                    {"messages": [x for x in sorted(self.messages.items())]},
                    room=sid,
                )
            else:
                # A todos si todavia no se hace
                self.server.emit("message_history", {"messages": [x for x in sorted(self.messages.items())]})
                self.history_sent = True

        logger.debug(f"{user.name} connected with sid {user.sid}")

    def on_migrate(self, _, vector_clock_inits, messages, min_user_count, history_sent):
        logger.debug("Starting on_migrate endpoint")
        # self.clock = self.clock.load_from(vector_clock_inits[0], vector_clock_inits[1])
        self.clock = self.clock.load_from(vector_clock_inits[0], vector_clock_inits[1])
        self.messages = messages
        self.__migrating = False
        self.history_sent = history_sent
        self.min_user_count = min_user_count
        self.cycle_th = Thread(target=self.migration_manager._server_cycle, daemon=True)
        self.cycle_th.start()

    def catch_all(self, event, sid, data):
        logger.warning(f"Catchall {event} from {sid} with data {data}")

    def on_disconnect(self, sid):
        # Obtener el usuario, si existe
        client = self.users.get_user_by_sid(sid)
        if client:
            logger.debug(f"User disconnected: {client.name}")

            # Notificar al resto que el usuario se desconecto
            self.server.emit(
                "server_message",
                {"message": f"\u274C {client.name} has disconnected from the server"},
            )

            # Eliminar al usuario del registro
            self.users.del_user(client.uuid)

    def on_chat(self, sid, data):
        """Maneja el broadcast de los chats"""
        # Obtener el cliente que mando el mensaje
        self.clock.receive_message(data)
        return True

    def _on_deliver_message(self, message: dict, message_index: int):
        uuid: str = message[SENDER_ID]
        logger.debug(f"Delivering message {message}")
        client = self.users.get_user_by_uuid(uuid)

        # Agregar mensaje al registro
        self.messages[message_index] = {"username": client.name, "message": message[MESSAGE]}

        # Enviar mensaje solo si se supero el limite inferior
        if client and (len(self.users) >= self.min_user_count or self.history_sent):
            for dest_uuid, user in self.users.users.items():
                try:
                    msg = self.clock.send_message(message[MESSAGE], dest_uuid)
                    msg["username"] = client.name
                    msg["index"] = message_index
                    self.server.emit("chat", msg, to=user.sid)
                except Exception as e:
                    logger.error(e)

    def _on_clock_deliver_message(self, message: dict):
        self.server_coord.request_next_index(message)

    def send_pause_messaging_signal(self, pause=True):
        self.__migrating = pause
        received = {uuid: False for uuid in self.users.users}

        def update(uuid):
            logger.debug(f"Received response from user with uuid {uuid}")
            received[uuid] = True

        for dest_uuid, user in self.users.users.items():
            self.server.emit(
                "pause_messaging",
                pause,
                to=user.sid,
                callback=lambda: update(dest_uuid),
            )

    def send_reconnect_signal(self):
        self.server.emit("reconnect")
        self.users = UserList()

    def addr_request(self, sid, data):
        dest_username = data["username"]
        dest_user = self.users.get_user_by_name(dest_username)
        if dest_user:
            return dest_user.uri, dest_user.uuid
        return None, None

    def cleanup(self):
        self.clock = VectorClock("server", self._on_clock_deliver_message)
        self.messages = {}
