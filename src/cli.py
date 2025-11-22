import argparse
import time
import queue
import random
import string
from src.channel import UnreliableChannel
from src.gbn import GBNSender, GBNReceiver
from src.sr import SRSender, SRReceiver


def generate_random_data(size: int) -> bytes:
    return "".join(
        random.choices(string.ascii_letters + string.digits, k=size)
    ).encode()


def run_experiment(
    protocol: str,
    data_size: int,
    loss_rate: float,
    corruption_rate: float,
    delay: float,
    reorder_rate: float,
    window_size: int,
    timeout: float,
):

    print(f"--- Starting Experiment: {protocol.upper()} ---")
    print(f"Data Size: {data_size} bytes")
    print(f"Loss Rate: {loss_rate}, Corruption Rate: {corruption_rate}")
    print(f"Delay: {delay}, Reorder Rate: {reorder_rate}")
    print(f"Window Size: {window_size}, Timeout: {timeout}")

    # Forward channel: Sender -> Receiver
    # Backward channel: Receiver -> Sender (ACKs)

    forward_channel = UnreliableChannel(loss_rate, corruption_rate, delay, reorder_rate)
    backward_channel = UnreliableChannel(
        loss_rate, corruption_rate, delay, reorder_rate
    )

    # Sender -> forward_channel -> receiver_input_queue -> Receiver
    # Receiver -> backward_channel -> sender_input_queue -> Sender

    if protocol == "gbn":
        receiver = GBNReceiver(backward_channel, None, window_size)  # type: ignore
        sender = GBNSender(
            forward_channel, receiver.receiver_queue, window_size, timeout
        )
        receiver.sender_queue = sender.sender_queue  

    elif protocol == "sr":
        receiver = SRReceiver(backward_channel, None, window_size)
        sender = SRSender(
            forward_channel, receiver.receiver_queue, window_size, timeout
        )
        receiver.sender_queue = sender.sender_queue

    # Generate data
    data = generate_random_data(data_size)

    # Start threads
    receiver.start()
    sender.start()

    start_time = time.time()
    sender.send_data(data)

    # Wait for completion
    # How do we know when it's done?
    # Receiver should have received all data.
    # But Receiver doesn't know total size.
    # We can check `len(receiver.get_received_data()) == data_size`.

    while True:
        received_len = len(receiver.get_received_data())
        if received_len >= data_size:
            break
        time.sleep(0.1)

        # Timeout safety
        if time.time() - start_time > timeout * data_size / 100 + 10:  # Rough timeout
            print("Experiment Timed Out!")
            break

    end_time = time.time()
    duration = end_time - start_time
    throughput = data_size / duration  # bytes per second

    print(f"Experiment Finished.")
    print(f"Time: {duration:.4f} s")
    print(f"Throughput: {throughput:.2f} B/s")

    # Verify data
    if receiver.get_received_data() == data:
        print("Data Integrity: PASS")
    else:
        print("Data Integrity: FAIL")
        print(f"Sent: {len(data)}, Received: {len(receiver.get_received_data())}")

    # Stop threads
    sender.stop()
    receiver.stop()


def main():
    parser = argparse.ArgumentParser(
        description="RDT Lab: Selective Repeat vs Go-Back-N"
    )
    parser.add_argument(
        "--protocol", choices=["gbn", "sr"], required=True, help="Protocol to use"
    )
    parser.add_argument("--size", type=int, default=10000, help="Data size in bytes")
    parser.add_argument(
        "--loss", type=float, default=0.0, help="Packet loss rate (0.0-1.0)"
    )
    parser.add_argument(
        "--corruption", type=float, default=0.0, help="Packet corruption rate (0.0-1.0)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.0, help="Average delay in seconds"
    )
    parser.add_argument(
        "--reorder", type=float, default=0.0, help="Reordering rate (0.0-1.0)"
    )
    parser.add_argument("--window", type=int, default=4, help="Window size")
    parser.add_argument("--timeout", type=float, default=1.0, help="Timeout in seconds")

    args = parser.parse_args()

    run_experiment(
        args.protocol,
        args.size,
        args.loss,
        args.corruption,
        args.delay,
        args.reorder,
        args.window,
        args.timeout,
    )


if __name__ == "__main__":
    main()
