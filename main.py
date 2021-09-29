from argparse import ArgumentParser
from time import sleep
from src.client.client_socket import ClientSockets
from src.server.MigrationManager import MigrationManager
from threading import Thread
import logging

logging.basicConfig(level=logging.DEBUG)

parser = ArgumentParser()

parser.add_argument(
    "--dns_ip",
    default="localhost",
    help="Domain name server ip",
    type=str,
)
parser.add_argument(
    "--dns_port",
    default=8000,
    help="Domain name server port",
    type=int,
)
parser.add_argument(
    "-u",
    "--server_uri",
    default="default_server@local",
    help="Server URI",
    type=str,
)
parser.add_argument(
    "-p",
    "--port",
    required=False,
    default=3000,
    help="The port to listen as the server.",
    type=int,
)
parser.add_argument(
    "-n",
    "--min_n",
    default=0,
    help="Minimum number of clients before starting the connection.",
    type=int,
)
parser.add_argument(
    "-s", "--start_as_server", action="store_true", help="Start this as acting server"
)

if __name__ == "__main__":
    args = parser.parse_args()

    # Server en otro thread
    server = MigrationManager(
        args.dns_ip, args.dns_port, args.server_uri, args.port, args.min_n
    )
    server_th = Thread(target=server.start, args=[args.start_as_server])
    server_th.start()

    # Cliente en thread principal
    client = ClientSockets(args.dns_ip, args.dns_port, args.server_uri)
    client.initialize()
