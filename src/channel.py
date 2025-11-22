import random
import time
import queue
import threading
from typing import Optional
from src.packet import Packet


class UnreliableChannel:
    """
    Simulates an unreliable channel with packet loss, corruption, delay, and reordering.
    """

    def __init__(
        self,
        loss_rate: float = 0.0,
        corruption_rate: float = 0.0,
        avg_delay: float = 0.0,
        reorder_rate: float = 0.0,
        seed: Optional[int] = None,
        observer=None,
    ):
        self.loss_rate = loss_rate
        self.corruption_rate = corruption_rate
        self.avg_delay = avg_delay
        self.reorder_rate = reorder_rate
        self.observer = observer
        if seed is not None:
            random.seed(seed)

        # Queue to hold packets in transit: (delivery_time, packet)
        self.packet_queue = queue.PriorityQueue()
        self.lock = threading.Lock()

    def send(self, packet: Packet, destination_queue: queue.Queue):
        """
        Sends a packet through the channel.
        """
        # Calculate delay first for visualization
        # Base delay
        delay = (
            self.avg_delay + random.uniform(-self.avg_delay * 0.5, self.avg_delay * 0.5)
            if self.avg_delay > 0
            else 0
        )

        # Reordering: add extra random delay to some packets
        if random.random() < self.reorder_rate:
            delay += random.uniform(
                0.1, 0.5
            )  # Add significant delay to cause reordering

        # Notify observer that packet is sent
        if self.observer:
            self.observer.packet_sent(packet, delay)

        # 1. Packet Loss
        if random.random() < self.loss_rate:
            if self.observer:
                # Simulate loss occurring mid-transit
                threading.Timer(
                    delay * random.uniform(0.2, 0.8),
                    self.observer.packet_lost,
                    args=[packet],
                ).start()
            return

        # 2. Corruption
        if random.random() < self.corruption_rate:
            # Corrupt the packet (e.g., flip a bit in payload or checksum)
            # For simplicity, we just change the checksum to be invalid
            packet.checksum = (packet.checksum + 1) % 0xFFFFFFFF
            if self.observer:
                self.observer.packet_corrupted(packet)

        delivery_time = time.time() + delay

        # We use a thread to deliver packets asynchronously
        threading.Thread(
            target=self._deliver, args=(packet, destination_queue, delay)
        ).start()

    def _deliver(self, packet: Packet, destination_queue: queue.Queue, delay: float):
        """Helper to deliver packet after delay."""
        if delay > 0:
            time.sleep(delay)
        destination_queue.put(packet)
        if self.observer:
            self.observer.packet_delivered(packet)
