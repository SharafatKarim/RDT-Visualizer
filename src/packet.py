import struct
import json
from typing import Optional
from src.utils import calculate_checksum


class Packet:
    """
    Represents a data packet in the RDT protocol.
    Structure:
    - seq_num (int): Sequence number
    - ack_num (int): Acknowledgment number
    - flags (int): Control flags (SYN, FIN, ACK, etc.)
    - payload (bytes): Data payload
    - checksum (int): Checksum for error detection
    """

    SYN = 0b001
    ACK = 0b010
    FIN = 0b100

    def __init__(
        self,
        seq_num: int,
        ack_num: int,
        flags: int,
        payload: bytes = b"",
        checksum: Optional[int] = None,
    ):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.payload = payload
        if checksum is None:
            self.checksum = self.calculate_checksum()
        else:
            self.checksum = checksum

    def calculate_checksum(self) -> int:
        """Calculates checksum over header fields and payload."""
        # Pack header fields: seq_num, ack_num, flags
        # We use a simple packing format.
        # Note: checksum field itself is NOT included in checksum calculation.
        header = struct.pack("!III", self.seq_num, self.ack_num, self.flags)
        return calculate_checksum(header + self.payload)

    def is_corrupt(self) -> bool:
        """Checks if the packet is corrupt."""
        return self.calculate_checksum() != self.checksum

    def to_bytes(self) -> bytes:
        """Serializes the packet to bytes."""
        # Format: Seq(4), Ack(4), Flags(4), Checksum(4), Payload_Len(4), Payload(...)
        payload_len = len(self.payload)
        header = struct.pack(
            "!IIIII", self.seq_num, self.ack_num, self.flags, self.checksum, payload_len
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "Packet":
        """Deserializes a packet from bytes."""
        if len(data) < 20:  # 5 * 4 bytes
            raise ValueError("Data too short to be a packet")

        seq_num, ack_num, flags, checksum, payload_len = struct.unpack(
            "!IIIII", data[:20]
        )
        payload = data[20 : 20 + payload_len]

        return cls(seq_num, ack_num, flags, payload, checksum)

    def __repr__(self):
        return f"Packet(seq={self.seq_num}, ack={self.ack_num}, flags={self.flags}, len={len(self.payload)})"
