"""Implementation of a simple Name Server with SSP (stub, scion pairs)
Chains, this is a simple solution for locating entities that is mainly
applicable to local-area networks.

 - Server should have a migration protocol: marshalls the


"""
from collections import defaultdict
import logging
import pickle as pkl
from datetime import datetime
import socket
from threading import Thread

from colorama.ansi import Fore
from ..utils.networking import get_public_ip

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(f"{Fore.GREEN}[DNS]{Fore.RESET}")


def ctime():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time


class NameServer:
    def __init__(self, host="localhost", port=8000, n=10):
        """Initializes a name server with forwarding pointers of the form
        (stub, scion) for clients stubs and server stubs.

        The objective of this class is to provide an approach for locating
        mobile entities via following a chain of forwarding pointers.

        Forwarding Pointer example: (stub, scion), where stub is the client
        stub and scion is the server stub. When the scion is null, the stub
        points to the actual object, else

        Parameters
        ----------
        host : int or str
            Machine on which the server will be running
        port : int
            Port on which the server will be listening for requests
        n : int
            Maximum number of processes to listen
        """
        self.host = host
        self.port = port
        self.n = n
        self.locations = defaultdict(list)  # {name: addr}

        # initialize NS
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(("0.0.0.0", self.port))
        self.s.listen(n)

        logger.debug(
            f"[{ctime()}] Name Server up and running on"
            f" IP: {self.host}, PORT: {self.port}"
        )

    def run(self):
        """Runs the Name Server.

        Incoming requests must come with the following structure:

        If the server is updating it's address:
        {
            'name': 'update_server',
            'addr': <server address>
        }

        If the client is requesting an address:

        {
            'name': 'addr_request',
            'uri': <uri>
        }

        if 'name' is 'server', then the message must come with a 'host' key
        with the new host location.
        if 'name' is 'client', the last locato
        """
        logger.debug(f"[{ctime()}] Accepting connections")
        while True:
            logger.debug(f"[{ctime()}] Waiting for next connection")
            (conn, addr) = self.s.accept()
            if conn:
                client_th = Thread(target=self.accept_connection, args=[conn, addr])
                client_th.start()

    def accept_connection(self, conn: socket.socket, addr):
        logger.debug(
            f"[{ctime()}] Accepted connection from " f"IP: {addr[0]}, PORT: {addr[1]}"
        )

        while True:
            try:
                data = conn.recv(1024)
                req = pkl.loads(data)

                if req["name"] == "update_server":
                    self.update_location(req["uri"], req["addr"])
                    msj = {
                        "name": "update_server_response",
                        "addr": self.get_s_last_location(req["uri"]),
                    }
                    conn.send(pkl.dumps(msj))
                    logger.debug(
                        f"[{ctime()}] Updated server last known location to:"
                        f" {req['addr']}"
                    )
                elif req["name"] == "addr_request":
                    msj = {
                        "name": "addr_response",
                        "addr": self.get_s_last_location(req["uri"]),
                        "req_uri": req["uri"],
                    }
                    conn.send(pkl.dumps(msj))
                    logger.debug(
                        f"[{ctime()}] Last known location sent to client: {req['uri']} -> {msj['addr']}"
                    )
                else:
                    # TODO: send empty message to sender
                    logger.debug(f"[{ctime()}] Message didnt match")
                    msj = {
                        "name": "empty",
                    }
                    conn.send(pkl.dumps(msj))
                break
            except pkl.UnpicklingError as e:
                logger.debug(e)
        logger.debug(
            f"[{ctime()}] Closing connection from " f"IP: {addr[0]}, PORT: {addr[1]}"
        )

        conn.close()

    def update_location(self, uri, host):
        """Receives a new IP from the server host and update the list
        of known locations

        Parameters
        ----------
        host : str
            New hos location
        """
        if len(self.locations[uri]) <= 2:
            self.locations[uri].append(host)
        else:
            self.locations[uri][-1] = host

    def get_s_last_location(self, uri):
        if len(self.locations[uri]):
            return self.locations[uri][-1]
        return None


def serve():
    HOST, PORT = get_public_ip()
    PORT = 8000 or PORT
    n = 10
    ns = NameServer(HOST, PORT, n)

    ns.run()


if __name__ == "__main__":
    serve()
