import time
import threading
from typing import List
from src.packet import Packet
from src.rdt_base import RDTSender, RDTReceiver
from src.channel import UnreliableChannel


class GBNSender(RDTSender):
    """
    Go-Back-N Sender.
    """

    def __init__(
        self,
        channel: UnreliableChannel,
        receiver_queue,
        window_size: int = 4,
        timeout: float = 1.0,
        observer=None,
    ):
        super().__init__(channel, receiver_queue, observer)
        self.window_size = window_size
        self.timeout = timeout
        self.base = 0
        self.next_seq_num = 0
        self.packets: List[Packet] = []  # Buffer to store all packets created from data
        self.timer = None
        self.lock = threading.Lock()

    def send_data(self, data: bytes):
        """
        Divides data into packets and starts sending.
        For simplicity, we assume this is called once with all data.
        """
        # Packetize data
        chunk_size = 1024
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            packet = Packet(
                seq_num=len(self.packets), ack_num=0, flags=0, payload=chunk
            )
            self.packets.append(packet)

        # Start sending loop
        threading.Thread(target=self._send_window, daemon=True).start()

    def _send_window(self):
        while self.running and self.base < len(self.packets):
            with self.lock:
                # Send packets within window
                while (
                    self.running
                    and self.next_seq_num < self.base + self.window_size
                    and self.next_seq_num < len(self.packets)
                ):
                    packet = self.packets[self.next_seq_num]
                    print(f"Sender: Sending packet {packet.seq_num}")
                    self.channel.send(packet, self.receiver_queue)

                    if self.base == self.next_seq_num:
                        self._start_timer()

                    self.next_seq_num += 1

            time.sleep(0.01)  # Yield to prevent busy waiting

    def _start_timer(self):
        if self.timer:
            self.timer.cancel()
        if self.running:
            self.timer = threading.Timer(self.timeout, self._timeout_handler)
            self.timer.start()

    def _stop_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _timeout_handler(self):
        if not self.running:
            return

        with self.lock:
            print(f"Sender: Timeout! Retransmitting from {self.base}")
            self._start_timer()
            # Retransmit all packets in window
            for i in range(self.base, self.next_seq_num):
                if not self.running:
                    break
                print(f"Sender: Retransmitting packet {self.packets[i].seq_num}")
                self.channel.send(self.packets[i], self.receiver_queue)

    def process_ack(self, packet: Packet):
        if packet.is_corrupt():
            print("Sender: Received corrupt ACK")
            return

        with self.lock:
            print(f"Sender: Received ACK {packet.ack_num}")
            # Cumulative ACK: ack_num is the next expected seq_num
            # So if we get ack_num, it means everything before ack_num is received.
            if packet.ack_num > self.base:
                self.base = packet.ack_num
                self._stop_timer()
                if self.base < self.next_seq_num:
                    self._start_timer()

    def stop(self):
        super().stop()
        self._stop_timer()


class GBNReceiver(RDTReceiver):
    """
    Go-Back-N Receiver.
    """

    def __init__(self, channel: UnreliableChannel, sender_queue, observer=None):
        super().__init__(channel, sender_queue, observer)
        self.expected_seq_num = 0

    def receive_packet(self, packet: Packet):
        if packet.is_corrupt():
            print("Receiver: Received corrupt packet")
            # Send ACK for last correctly received packet (expected_seq_num - 1)
            # But if expected_seq_num is 0, we can't ack -1.
            # In GBN, we usually just re-send the last ACK.
            self._send_ack(self.expected_seq_num)
            return

        print(f"Receiver: Received packet {packet.seq_num}")
        if packet.seq_num == self.expected_seq_num:
            self.received_data.append(packet.payload)
            self.expected_seq_num += 1
            self._send_ack(self.expected_seq_num)
        else:
            print(f"Receiver: Out of order packet {packet.seq_num}, expected {self.expected_seq_num}")
            self._send_ack(self.expected_seq_num)

    def _send_ack(self, ack_num: int):
        ack_packet = Packet(seq_num=0, ack_num=ack_num, flags=Packet.ACK)
        self.channel.send(ack_packet, self.sender_queue)
