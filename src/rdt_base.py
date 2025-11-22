from abc import ABC, abstractmethod
import queue
import threading
from src.packet import Packet
from src.channel import UnreliableChannel


class RDTSender(ABC):
    """
    Abstract base class for RDT Sender.
    """

    def __init__(
        self, channel: UnreliableChannel, receiver_queue: queue.Queue, observer=None
    ):
        self.channel = channel
        self.receiver_queue = receiver_queue
        self.sender_queue = queue.Queue()  # Queue for ACKs coming back from receiver
        self.running = True
        self.observer = observer

    @abstractmethod
    def send_data(self, data: bytes):
        """Called by the application layer to send data."""
        pass

    @abstractmethod
    def process_ack(self, packet: Packet):
        """Process incoming ACK packets."""
        pass

    def log(self, message: str):
        if self.observer:
            self.observer.log(f"Sender: {message}")

    def start(self):
        """Starts the sender thread to listen for ACKs."""
        threading.Thread(target=self._listen_for_acks, daemon=True).start()

    def _listen_for_acks(self):
        while self.running:
            try:
                packet = self.sender_queue.get(timeout=0.1)
                self.process_ack(packet)
            except queue.Empty:
                continue

    def stop(self):
        self.running = False


class RDTReceiver(ABC):
    """
    Abstract base class for RDT Receiver.
    """

    def __init__(
        self, channel: UnreliableChannel, sender_queue: queue.Queue, observer=None
    ):
        self.channel = channel
        self.sender_queue = sender_queue
        self.receiver_queue = queue.Queue()  # Queue for Data packets coming from sender
        self.running = True
        self.received_data = []  # Store received payloads
        self.observer = observer

    @abstractmethod
    def receive_packet(self, packet: Packet):
        """Process incoming data packets."""
        pass

    def log(self, message: str):
        if self.observer:
            self.observer.log(f"Receiver: {message}")

    def start(self):
        """Starts the receiver thread to listen for packets."""
        threading.Thread(target=self._listen_for_packets, daemon=True).start()

    def _listen_for_packets(self):
        while self.running:
            try:
                packet = self.receiver_queue.get(timeout=0.1)
                self.receive_packet(packet)
            except queue.Empty:
                continue

    def get_received_data(self) -> bytes:
        return b"".join(self.received_data)

    def stop(self):
        self.running = False
