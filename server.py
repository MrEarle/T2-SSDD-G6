from argparse import ArgumentParser
from src.server.MigrationManager import MigrationManager
from src.server.Server import Server
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

    server = MigrationManager(
        args.dns_ip, args.dns_port, args.server_uri, args.port, args.min_n
    )
    server.start(start_as_server=args.start_as_server)

    logging.debug("Exit")
