from argparse import ArgumentParser
from src.client.client_socket import ClientSockets
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
    "--uri",
    default="default_server@local",
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
    print(args.uri)
    print(args.min_n)

    logging.debug("Setting up client")
    client = ClientSockets(args.dns_ip, args.dns_port, args.uri)
    client.initialize()

    logging.debug("Exit")
