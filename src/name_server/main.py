"""Implementation of a simple Name Server with SSP (stub, scion pairs)
Chains, this is a simple solution for locating entities that is mainly
applicable to local-area networks.

 - Server should have a migration protocol: marshalls the


"""
import pickle as pkl
import os
from datetime import datetime
from socket import *


def ctime():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    return current_time


class NameServer:
    def __init__(self, host='localhost', port=8000, n=10):
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
        self.locations = []

        # initialize NS
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.bind((self.host, self.port))
        self.s.listen(n)

        print(f'\n[{ctime()}] Name Server up and running on'
              f' IP: {self.host}, PORT: {self.port}')

    def run(self):
        """Runs the Name Server.

        Incoming requests must come with the following structure:

        {
            'name': 'server',
            'host': ...
        }

        in case the sender is the app server, else

        {
            'name': 'client',
            'host': ...
        }

        if 'name' is 'server', then the message must come with a 'host' key
        with the new host location.
        if 'name' is 'client', the last locato
        """
        while True:
            (conn, addr) = self.s.accept()
            print(f'[{ctime()}] Accepted connection from '
                  f'IP: {addr[0]}, PORT: {addr[1]}')

            data = conn.recv(1024)
            req = pkl.loads(data)

            if req['name'] == 'server':
                self.update_location(req['host'])
                print(f"[{ctime()}] Updated server last known location to:"
                      f" {req['host']}")
            elif req['name'] == 'client':
                msj = {'name': 'NS', 'msj': self.get_s_last_location()}
                conn.send(pkl.dumps(msj))
                print(f"[{ctime()}] Last known location sent to client:"
                      f" {req['host']}")
            else:
                # TODO: send empty message to sender
                pass

    def update_location(self, host):
        """Receives a new IP from the server host and update the list
        of known locations

        Parameters
        ----------
        host : str
            New hos location
        """
        if len(self.locations) <= 2:
            self.locations.append(host)
        else:
            self.locations[-1] = host

    def get_s_last_location(self):
        return self.locations[-1]


if __name__ == "__main__":
    HOST = '192.168.1.101'
    PORT = 8000
    n = 10
    ns = NameServer(HOST, PORT, n)

    ns.run()
