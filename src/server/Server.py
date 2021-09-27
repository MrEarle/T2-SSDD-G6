import logging
from threading import Thread
from typing import TypedDict

import socketio
from colorama import Fore as Color
from werkzeug.serving import make_server

from src.utils.vectorClock import MESSAGE, SENDER_ID, VectorClock

from .Users import UserList

logger = logging.getLogger(f"{Color.GREEN}[Server]{Color.RESET}")
authType = TypedDict("Auth", {"username": str, "publicUri": str})


class Server:
    def __init__(self, port: int = 3000, min_user_count: int = 0) -> None:
        self.server = socketio.Server(cors_allowed_origins="*")
        self.app = socketio.WSGIApp(self.server)

        self.port = port
        self.__created_server = make_server(
            "127.0.0.1",
            port,
            self.app,
            threaded=True,
        )
        self.__created_server_th: Thread = None

        self.users = UserList()
        self.history_sent = False
        self.min_user_count = min_user_count
        self.messages = []

        self.setup_handlers()

        self.clock = VectorClock("server", self.__on_deliver_message)

    def setup_handlers(self):
        self.server.on("connect", self.on_connect)
        self.server.on("disconnect", self.on_disconnect)
        self.server.on("chat", self.on_chat)
        self.server.on("addr_request", self.addr_request)
        self.server.on("*", self.catch_all)

    def serve(self):
        logger.debug(f"Running App on port {self.port}")
        self.__created_server_th = Thread(
            target=self.__created_server.serve_forever, daemon=True
        )
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
        logger.debug(f"User logging in with auth: {auth}")
        user = self.users.add_user(auth["username"], sid, auth["publicUri"])

        if user is None:
            logger.debug(f'Username {auth["username"]} is already taken')
            raise ConnectionRefusedError("Username is invalid or already taken")

        self.server.emit(
            "server_message",
            {"message": f'\u2713 {auth["username"]} has connected to the server'},
        )

        self.server.emit("send_uuid", user.uuid, room=sid)

        # Si se supero el limite inferior de usuarios conectados, mandar la historia
        if len(self.users) >= self.min_user_count:
            logger.debug(f"Sending history")

            if self.history_sent:
                # Solo al cliente conectado si ya se mando a todos
                self.server.emit(
                    "message_history",
                    {"messages": self.messages},
                    room=sid,
                )
            else:
                # A todos si todavia no se hace
                self.server.emit("message_history", {"messages": self.messages})
                self.history_sent = True

        logger.debug(f"{user.name} connected with sid {user.sid}")

    def catch_all(self, event, sid, data):
        logger.warning(f"Catchall {event} from {sid} with data {data}")

    def on_disconnect(self, sid):
        # Obtener el usuario, si existe
        logger.debug("User disconnected")
        client = self.users.get_user_by_sid(sid)
        if client:
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

    def __on_deliver_message(self, message: dict):
        uuid: str = message[SENDER_ID]
        logger.debug(f"Delivering message {message}")
        client = self.users.get_user_by_uuid(uuid)

        # Agregar mensaje al registro
        self.messages.append({"username": client.name, "message": message[MESSAGE]})

        # Enviar mensaje solo si se supero el limite inferior
        if client and (len(self.users) >= self.min_user_count or self.history_sent):
            for dest_uuid, user in self.users.users.items():
                try:
                    msg = self.clock.send_message(message[MESSAGE], dest_uuid)
                    msg["username"] = client.name
                    self.server.emit("chat", msg, to=user.sid)
                except Exception as e:
                    logger.error(e)

    def send_pause_messaging_signal(self, pause=True):
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

    def addr_request(self, sid, data):
        dest_username = data["username"]
        dest_user = self.users.get_user_by_name(dest_username)

        return dest_user.uri, dest_user.uuid
