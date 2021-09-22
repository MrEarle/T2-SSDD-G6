from collections import defaultdict
from functools import wraps
from threading import Lock
from copy import deepcopy
from typing import Callable, List

MESSAGE = "message"
TIMESTAMP = "timestamp"
VECTORS = "vectors"


def create_with_vector_locks(lock_names: List[str]):
    lock_names = lock_names.sort()

    def with_vector_locks(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for lock_name in lock_names:
                self.locks[lock_name].acquire()
                result = func(self, *args, **kwargs)
                self.locks[lock_name].release()
                return result

        return wrapper

    return with_vector_locks


class VectorClock:
    def __init__(self, idx: str, onDeliverMessage: Callable[[dict], None]) -> None:
        self.idx = idx
        # { destination_id: vector_timestamp }
        self.v_p = defaultdict(lambda: defaultdict(lambda: 0))

        # Logical time of sending message m
        self.t_m = defaultdict(lambda: 0)

        # Delayed message queue
        self.delayed_queue = []

        # Locks
        self.lock_names = ["v_lock", "t_lock", "d_lock"]
        self.locks = {x: Lock() for x in self.lock_names}

        # Callback when message is delivered
        self.onDeliverMessage = onDeliverMessage

    @create_with_vector_locks(["t_lock", "v_lock"])
    def send_message(self, message_text: str, dest_idx: str):
        """
        Public method for when a message is being sent. Executes vector clock logic:

        P_i sends a message to P_j

        Parameters:
        message_text: Message string to send
        dest_idx: Destination id

        Returns:
        dict: Dictionary containing message text and clock related values
        """
        # P_i sends message m, timestamped t_m, and V_i to process P_j
        self.t_m[self.idx] += 1
        message = {
            MESSAGE: message_text,
            TIMESTAMP: deepcopy(self.t_m),
            VECTORS: deepcopy(self.v_p),
        }

        # P_i sets V_i[j] = t_m
        self.v_p[dest_idx] = self.t_m

        return message

    @create_with_vector_locks(["t_lock", "v_lock"])
    def __should_delay_message(self, message: dict) -> bool:
        """
        When Pj, j ≠ i, receives m, it delays the message’s delivery if both:
            - V_m[j] is set; and
            - V_m[j] < t_j

        Parameters:
        message (dict): Dictionary of the received message. Contains the senders
        timestamp and vector clock.

        Returns:
        bool: Wether the message should be delayed
        """
        vectors = message[VECTORS]

        # V_m[j] is set
        if self.idx in vectors:
            idxs = set(self.v_p.keys())
            idxs.update(vectors.keys())

            # v_m[j] < t_j
            for idx in idxs:
                if idx not in vectors[self.idx]:
                    continue

                if not (vectors[self.idx][idx] < self.t_m[idx]):
                    return False

            return True

        return False

    @create_with_vector_locks(["t_lock"])
    def update_vector_clock(self, timestamp: dict):
        """
        Update Pj's vector clock.

        Parameters:
        timestamp (dict): Dictionary containing the timestamp of the
        senders vector clock. Should be included in the received message.
        """
        idxs = set(self.t_m.keys())
        idxs.update(timestamp.keys())

        for idx in idxs:
            if idx in timestamp:
                self.t_m[idx] = max(self.t_m[idx], timestamp[idx])

    @create_with_vector_locks(["v_lock"])
    def __deliver_message(self, message: dict):
        """
        When the message is delivered to Pj, update all set elements of Vj
        with the corresponding elements of Vm, except for Vj[j]

        Parameters:
        message (dict): Dictionary of the received message. Contains the senders
        timestamp and vector clock.

        """
        vectors = message[VECTORS]
        for idx in vectors:
            if idx == self.idx:
                continue

            if idx not in self.v_p:
                # If Vj[k] is uninitialized and Vm[k] is initialized, set Vj[k] = Vm[k].
                self.v_p[idx] = vectors[idx]
            else:
                #  If both Vj[k] and Vm[k] are initialized, set Vj[k][k′] = max(Vj[k][k′], Vm[k][k′]) for all k′ = 1, …, n
                inner_idxs = set(self.v_p.keys())
                inner_idxs.update(vectors.keys())
                for inner_idx in inner_idxs:
                    if inner_idx in vectors:
                        self.v_p[idx][inner_idx] = max(
                            self.v_p[idx][inner_idx], vectors[idx][inner_idx]
                        )

        # Message delivery callback
        self.onDeliverMessage(message)

    @create_with_vector_locks(["d_lock"])
    def receive_message(self, message: dict):
        """
        Public function to receive a message. Executes vector clock logic.

        Parameters:
        message (dict): Dictionary of the received message. Contains the senders
        timestamp and vector clock.
        """
        if self.__should_delay_message(message):
            self.delayed_queue.append(message)
        else:
            self.__deliver_message(message)

        self.update_vector_clock(timestamp=message[TIMESTAMP])

    def __check_delayed_messages(self):
        """Check buffered messages to see if any can be delivered"""
        self.locks["d_lock"].acquire()
        for i in range(len(self.delayed_queue)):
            if self.__should_delay_message(self.delayed_queue[i]):
                continue

            message = self.delayed_queue.pop(i)
            self.__deliver_message(message)
            self.locks["d_lock"].release()

            self.__check_delayed_messages()
            return

        self.locks["d_lock"].release()
