from .gui_socketio import GUI
from collections import deque

import socketio
import logging
from colorama import Fore as Color


logger = logging.getLogger(f"{Color.RED}[ClientSockets]{Color.RESET}")


class ClientSockets:
    def __init__(self, server_uri: str) -> None:
        self.server_uri = server_uri
        self.gui = GUI(
            self.server_connect, self.send_private_message, self.send_message
        )
        # self.p2p = P2P()

        # Queue for outbound messages.
        # Should only send a message if the previous one was received by the server.
        self.__outbound = deque()
        self.__sendNext = False

    def initialize(self):
        # Initialize connection to server
        self.initialize_server_connection()

        # Initialize local server for p2p connections
        # self.p2p.initialize_server(self.gui)

        # Get public url and port for p2p connection
        # self.public_url, self.port = self.p2p.start()

        # Deploy the chat GUI
        self.gui.initialize()

    def initialize_server_connection(self):
        # Initialize connection to server
        self.server_io = socketio.Client(
            logger=True,
        )

        # Register event handlers
        self.server_io.on("connect", self.connect)
        self.server_io.on("server_message", self.server_message)
        self.server_io.on("chat", self.chat_message)
        self.server_io.on("chat_message_history", self.chat_message_history)

    def connect(self):
        logger.debug("Initializing chat GUI")
        self.gui.onConnect()

        # Start the message sending from queue in the background process
        logger.debug("Starting message delivery queue")
        self.server_io.start_background_task(self.__run)

    def server_message(self, data):
        # Cuando llega un mensaje del server, agregarlo en la gui
        self.gui.addMessage(data["message"])

    def chat_message(self, data):
        # Cuando llega un mensaje de un usuario, formatearlo
        # y agregarlo en la gui
        logger.debug(f"Chat received {data}")
        self.gui.addMessage(f"<{data['username']}> {data['message']}")

    def chat_message_history(self, data):
        # Si llega  la historia de mensaje, formatearlos y agregarlos
        # a la gui
        for msg in data["messages"]:
            self.gui.addMessage(f"<{msg['username']}> {msg['message']}")

    def __setSendNext(self, val: bool):
        # Utility function
        logger.debug("Send next")
        self.__sendNext = val

    def __run(self):
        # Constantly checks the queue for messages to send.
        # Only sends a message if the previous one has been
        # acknowledged by the server.
        self.__sendNext = True
        while True:
            if self.__outbound and self.__sendNext:
                logger.debug(f"Outbound length: {len(self.__outbound)}")
                # Prevent other messages from being sent
                self.__sendNext = False

                # Get next message to send
                msg = self.__outbound.popleft()

                # Send message to server, and allow next message to be sent
                # when the server responds to this message.
                logger.debug("Emmiting message to server")
                self.server_io.emit(
                    "chat",
                    msg,
                    callback=lambda _: self.__setSendNext(True),
                )

            # Yield the CPU
            self.server_io.sleep(1e-4)  # 100 usec

    def server_connect(self, name):
        # Connect to the server.
        # Sends session information, such as name, port and p2p server url.
        logger.debug(f"Connecting to server {self.server_uri}")
        self.server_io.connect(
            self.server_uri,
            auth={"username": name, "publicUri": ""},  # TODO: Public URI
        )

    def send_message(self, message: str):
        # Appends a message to the outbound queue.
        # See __run for message sending.
        # message = self.clock.send_message(message, "server")
        logger.debug(f"Sending message")
        self.__outbound.append(message)

    # def __send_private_message(self, addr, username, message, dest_user):
    #     # Check if addr is valid. If it is None, destination user is not
    #     # connected to the server.
    #     if addr is None:
    #         self.gui.addMessage(f"User {dest_user} is not connected")
    #     else:
    #         self.p2p.send_private_message(addr, username, message, dest_user)

    def send_private_message(self, dest_user: str, username: str, message: str):
        pass

    #     # Send a private message via p2p server
    #     try:
    #         # Ask server for destination p2p url.
    #         # Then, send the message to that url.
    #         self.server_io.emit(
    #             "addr_request",
    #             {"username": dest_user},
    #             callback=lambda addr: self.__send_private_message(
    #                 addr, username, message, dest_user
    #             ),
    #         )
    #     except TypeError:
    #         self.gui.addMessage(
    #             "There was an error sending the private message, please try again."
    #         )
