from typing import TypedDict
from socketio import Server
from threading import Lock

authType = TypedDict("Auth", {"username": str, "publicUri": str})


class ServerCoordinator:
    def __init__(self, socketio: Server, server):
        self.socketio = socketio
        self.server = server

        self._indexLock = Lock()

    def setupCoordinatorHandlers(self):
        # TODO: Registrar los metodos de coordinacion aca
        # e.g: self.socketio.on('event', self.event)
        self.socketio.on("request_next_index", self.on_request_next_index)
        pass

    def on_connect_other_server(self, sid: str, auth: authType):
        pass

    def on_request_next_index(self, data):
        """Determina el indice a asignar al mensaje que llegó"""

        # Calcular el indice a asignar
        with self._indexLock:
            remote_next_index = data["next_index"]  # Indice a asignar segun otro server
            # TODO: Implementar variable self.server.next_index
            # Indice a asignar segun este server
            local_next_index = self.server.next_index
            # Indice a asignar segun ambos
            next_index = max(remote_next_index, local_next_index)

            # Actualizar localmente el siguiente indice
            self.server.next_index = next_index + 1

            message = data["message"]
            # TODO: Actualzar esta funcion
            self.server._on_deliver_message(message, next_index)

        return {"next_index": next_index}

    def request_next_index(self, data):
        """Coordinar con el otro server para asignar indice al mensaje"""

        self._indexLock.acquire()
        try:

            def callback(response: dict):
                message = data["message"]
                self.server._on_deliver_message(message, response["next_index"])
                self.server.next_index = response["next_index"] + 1
                self._indexLock.release()

            self.socketio.emit("request_next_index", data, callback)
        except Exception as e:
            print(e)
            self._indexLock.release()
