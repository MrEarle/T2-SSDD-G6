from argparse import ArgumentParser
from src.server.Server import Server
import logging

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
    print(args.uri)
    print(args.min_n)

    server = Server(args.min_n)
    server.serve()

    logging.debug("Exit")