from collections import deque
from typing import TypedDict
from socketio import Server, Client
from threading import Lock
from time import sleep

authType = TypedDict("Auth", {"username": str, "publicUri": str})


class ServerCoordinator:
    def __init__(self, socketio: Server, server):
        self.socketio = socketio
        self.server = server

        self.coordinator_client: Client = None
        self.other_server_sid = None

        self._indexLock = Lock()
        self.message_queue = deque()

    def setupCoordinatorHandlers(self):
        # TODO: Registrar los metodos de coordinacion aca
        # e.g: self.socketio.on('event', self.event)
        self.socketio.on("request_next_index", self.on_request_next_index)

    def on_connect_other_server(self, sid: str, auth: authType):
        self.other_server_sid = sid

    def connect(self):
        while True:
            try:
                # 1. TODO: Pedir direccion a DNS
                # ========BENJA LEPE=======
                addr = ""
                # TODO: Implementar esto en el DNS
                # 2. TODO: Intentar conectar
                client = Client()
                client.connect(addr, auth={})  # Incluir en auth los headers indicando tipo de conexion
                # ==========LEPE===========
                # 3. TODO: Al conectar, setear los handlers
                client.on("disconnect", self.on_disconnect)
                # 4. TODO: Si todo funciona, terminar loop
                self.coordinator_client = client
                return
            except Exception:
                sleep(0.1)

    def on_disconnect(self):
        self.coordinator_client = None
        self.connect()
        self._desenqueue_messages()

    def on_request_next_index(self, data):
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

            message = data["message"]
            self.server._on_deliver_message(message, next_index)

        return {"next_index": next_index}

    def request_next_index(self, data):
        """Coordinar con el otro server para asignar indice al mensaje"""

        def callback(response: dict):
            with self._indexLock:
                # Cuando el otro server responde, se asigna el indice al mensaje
                message = data["message"]
                self.server._on_deliver_message(message, response["next_index"])
                self.server.next_index = max(self.server.next_index, response["next_index"]) + 1

        if self.other_server_sid and self.coordinator_client:
            try:
                with self._indexLock:
                    # Preguntar al otro server que indice poner al mensaje
                    data["next_index"] = self.server.next_index
                    self.coordinator_client.emit("request_next_index", data=data, callback=callback)
            except Exception:
                self.message_queue.append(data)
        else:
            # Se encola en mensaje si no se puede mandar
            self.message_queue.append(data)

    def _desenqueue_messages(self):
        while self.message_queue:
            message = self.message_queue.pop()
            self.request_next_index(message)
            sleep(0.1)
