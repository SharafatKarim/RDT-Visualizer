import time
import threading
from typing import List, Dict
from src.packet import Packet
from src.rdt_base import RDTSender, RDTReceiver
from src.channel import UnreliableChannel


class SRSender(RDTSender):
    """
    Selective Repeat Sender.
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
        self.packets: List[Packet] = []
        self.acked: List[bool] = []
        self.packet_timers: Dict[int, threading.Timer] = {}
        self.lock = threading.Lock()

    def send_data(self, data: bytes):
        chunk_size = 1024
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            packet = Packet(
                seq_num=len(self.packets), ack_num=0, flags=0, payload=chunk
            )
            self.packets.append(packet)
            self.acked.append(False)

        threading.Thread(target=self._send_window, daemon=True).start()

    def _send_window(self):
        while self.running and self.base < len(self.packets):
            with self.lock:
                while (
                    self.running
                    and self.next_seq_num < self.base + self.window_size
                    and self.next_seq_num < len(self.packets)
                ):
                    self._send_packet(self.next_seq_num)
                    self.next_seq_num += 1
            time.sleep(0.01)

    def _send_packet(self, seq_num: int):
        if not self.running:
            return
        packet = self.packets[seq_num]
        print(f"SR Sender: Sending packet {seq_num}")
        self.channel.send(packet, self.receiver_queue)
        self._start_timer(seq_num)

    def _start_timer(self, seq_num: int):
        if seq_num in self.packet_timers:
            self.packet_timers[seq_num].cancel()

        if self.running:
            timer = threading.Timer(self.timeout, self._timeout_handler, args=[seq_num])
            self.packet_timers[seq_num] = timer
            timer.start()

    def _stop_timer(self, seq_num: int):
        if seq_num in self.packet_timers:
            self.packet_timers[seq_num].cancel()
            del self.packet_timers[seq_num]

    def _timeout_handler(self, seq_num: int):
        if not self.running:
            return
        with self.lock:
            if not self.acked[seq_num]:
                print(f"SR Sender: Timeout! Retransmitting packet {seq_num}")
                self._send_packet(seq_num)

    def process_ack(self, packet: Packet):
        if packet.is_corrupt():
            return

        with self.lock:
            ack_num = packet.ack_num
            print(f"SR Sender: Received ACK {ack_num}")
            if self.base <= ack_num < self.next_seq_num:
                if not self.acked[ack_num]:
                    self.acked[ack_num] = True
                    self._stop_timer(ack_num)

                    # Advance base if possible
                    while self.base < len(self.packets) and self.acked[self.base]:
                        self.base += 1

    def stop(self):
        super().stop()
        with self.lock:
            for timer in self.packet_timers.values():
                timer.cancel()
            self.packet_timers.clear()


class SRReceiver(RDTReceiver):
    """
    Selective Repeat Receiver.
    """

    def __init__(
        self,
        channel: UnreliableChannel,
        sender_queue,
        window_size: int = 4,
        observer=None,
    ):
        super().__init__(channel, sender_queue, observer)
        self.window_size = window_size
        self.base = 0
        self.buffer: Dict[int, Packet] = {}  # Buffer for out-of-order packets

    def receive_packet(self, packet: Packet):
        if packet.is_corrupt():
            print("SR Receiver: Received corrupt packet")
            return

        seq_num = packet.seq_num
        print(f"SR Receiver: Received packet {seq_num}")

        if self.base <= seq_num < self.base + self.window_size:
            # Inside window
            self._send_ack(seq_num)
            if seq_num not in self.buffer:
                self.buffer[seq_num] = packet

            # Deliver consecutive packets
            while self.base in self.buffer:
                self.received_data.append(self.buffer[self.base].payload)
                del self.buffer[self.base]
                self.base += 1

        elif self.base - self.window_size <= seq_num < self.base:
            # Already received, re-ACK
            self._send_ack(seq_num)

    def _send_ack(self, ack_num: int):
        ack_packet = Packet(seq_num=0, ack_num=ack_num, flags=Packet.ACK)
        self.channel.send(ack_packet, self.sender_queue)
