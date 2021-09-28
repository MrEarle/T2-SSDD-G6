from argparse import ArgumentParser
import asyncio
from src.client.p2p import P2P
from src.client.client_socket import ClientSockets
from src.server.MigrationManager import MigrationManager
import eventlet
import logging

eventlet.monkey_patch()

logging.basicConfig(level=logging.DEBUG)

parser = ArgumentParser()

parser.add_argument(
    "-u",
    "--uri",
    required=False,
    help="The server URI to connect to. Leave blank to start as the server",
    type=str,
)
parser.add_argument(
    "-n",
    "--min_n",
    default=0,
    help="Minimum number of clients before starting the connection.",
    type=int,
)


if __name__ == "__main__":
    args = parser.parse_args()

    if not args.uri:
        server = MigrationManager(args.min_n)
        server_th = eventlet.spawn(server.serve)

    logging.debug("Setting up client")
    client = ClientSockets("http://127.0.0.1:3000/")
    client.initialize()

    if server_th:
        server_th.wait()

    logging.debug("Exit")
