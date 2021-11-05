from collections import deque
import logging
from typing import TypedDict
from socketio import Server, Client
from threading import Lock
from time import sleep
from colorama import Fore as Color

logger = logging.getLogger(f"{Color.LIGHTMAGENTA_EX}[Coordinator]{Color.RESET}")

authType = TypedDict("Auth", {"username": str, "publicUri": str})


class ServerCoordinator:
    def __init__(self, socketio: Server, server):
        self.socketio = socketio
        self.server = server

        self.coordinator_client: Client = None
        self.other_server_sid = None

        self._indexLock = Lock()
        self.message_queue = deque()
        self.setupCoordinatorHandlers()

    def setupCoordinatorHandlers(self):
        # TODO: Registrar los metodos de coordinacion aca
        # e.g: self.socketio.on('event', self.event)
        self.socketio.on("request_next_index", self.on_request_next_index)
        self.socketio.on("server_messages_request", self.on_ask_for_messages)

    def on_connect_other_server(self, sid: str, auth: authType):
        self.other_server_sid = sid
        self.connect()

    def connect(self):
        self.socketio.start_background_task(self._connect)

    def disconnect(self):
        self.on_disconnect()

    def _connect(self):
        while True:
            try:
                if self.coordinator_client and self.coordinator_client.connected:
                    return
                #  Pedir direccion a DNS
                addr = self.server.migration_manager.get_replica_address()
                if addr:
                    # Intentar conectar
                    client = Client()
                    client.connect(
                        addr,
                        auth={
                            "replica_connection": True,
                        },
                    )

                    logger.debug(f"Connected to other server at {addr}")

                    # 3. TODO: Al conectar, setear los handlers
                    client.on("disconnect", self.on_disconnect)
                    # 4. TODO: Si todo funciona, terminar loop
                    self.coordinator_client = client
                    self.ask_for_messages()
                    self._desenqueue_messages()
                    return
            except Exception:
                logger.debug(f"Tried connecting to other server and failed")

            sleep(0.1)

    def ask_for_messages(self):
        def callback(remote_messages):
            with self._indexLock:
                self.server.messages.update(remote_messages)
                if len(self.server.messages):
                    self.server.next_index = max(i for i in self.server.messages) + 1

        self.coordinator_client.emit("server_messages_request", data=self.server.next_index, callback=callback)

    def on_ask_for_messages(self, sid: str, remote_next_index: int):
        messages = {k: v for k, v in self.server.messages.items() if k >= remote_next_index}
        return messages

    def on_disconnect(self):
        if self.coordinator_client:
            self.coordinator_client.disconnect()
        self.coordinator_client = None
        self.connect()

    def on_request_next_index(self, sid: str, data: dict):
        """Determina el indice a asignar al mensaje que llegó"""

        # Calcular el indice a asignar
        with self._indexLock:
            # Indice a asignar segun otro server
            remote_next_index = data["next_index"]

            # Indice a asignar segun este server
            local_next_index = self.server.next_index

            # Indice a asignar segun ambos
            next_index = max(remote_next_index, local_next_index)

            # Actualizar localmente el siguiente indice
            self.server.next_index = max(self.server.next_index, next_index) + 1

            self.server._on_deliver_message(data, next_index)

        return next_index

    def request_next_index(self, data):
        """Coordinar con el otro server para asignar indice al mensaje"""

        def callback(next_index: int):
            with self._indexLock:
                # Cuando el otro server responde, se asigna el indice al mensaje
                self.server._on_deliver_message(data, next_index)
                self.server.next_index = max(self.server.next_index, next_index) + 1

        logger.debug(f"Comunicating with other server. data={data}")
        if self.coordinator_client and self.coordinator_client.connected:
            try:
                with self._indexLock:
                    # Preguntar al otro server que indice poner al mensaje
                    data["next_index"] = self.server.next_index
                    self.coordinator_client.emit("request_next_index", data=data, callback=callback)
            except Exception as e:
                logger.debug(f"Could not comunicate with other server. Queuing message")
                logger.warning(e)
                self.message_queue.append(data)
        else:
            # Se encola en mensaje si no se puede mandar
            logger.debug(f"No other server present. Queueing message")
            self.message_queue.append(data)

    def _desenqueue_messages(self):
        while self.message_queue:
            message = self.message_queue.pop()
            self.request_next_index(message)
            sleep(0.1)
