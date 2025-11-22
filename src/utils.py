import zlib


def calculate_checksum(data: bytes) -> int:
    """
    Calculates the CRC32 checksum of the given data.
    """
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_checksum(data: bytes, checksum: int) -> bool:
    """
    Verifies if the data matches the checksum.
    """
    return calculate_checksum(data) == checksum
