from argparse import ArgumentParser
from src.server.MigrationManager import MigrationManager
from src.server.Server import Server
import logging

logging.basicConfig(level=logging.DEBUG)

parser = ArgumentParser()

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


if __name__ == "__main__":
    args = parser.parse_args()
    print(args.port)
    print(args.min_n)

    server = MigrationManager(args.port, args.min_n)
    server.start()

    logging.debug("Exit")
