import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import threading
import time
import random
import string
from src.packet import Packet
from src.channel import UnreliableChannel
from src.gbn import GBNSender, GBNReceiver
from src.sr import SRSender, SRReceiver


class UIObserver:
    def __init__(self, event_queue):
        self.event_queue = event_queue

    def packet_sent(self, packet, delay):
        self.event_queue.put(("SENT", packet, delay, time.time()))

    def packet_lost(self, packet):
        self.event_queue.put(("LOST", packet))

    def packet_corrupted(self, packet):
        self.event_queue.put(("CORRUPT", packet))

    def packet_delivered(self, packet):
        self.event_queue.put(("DELIVERED", packet))

    def log(self, message):
        self.event_queue.put(("LOG", message))


class RDTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RDT Protocol Visualization")
        self.root.geometry("1000x700")

        self.event_queue = queue.Queue()
        self.observer = UIObserver(self.event_queue)

        self.running_experiment = False
        self.sender = None
        self.receiver = None
        self.animations = (
            []
        )  # List of active animations: {'id': item_id, 'start_time': t, 'end_time': t, 'start_x': x, 'end_x': x, 'y': y, 'color': c}

        self._setup_ui()
        self._start_ui_loop()

    def _setup_ui(self):
        # Configuration Frame
        config_frame = ttk.LabelFrame(self.root, text="Configuration")
        config_frame.pack(fill="x", padx=10, pady=5)

        # Protocol
        ttk.Label(config_frame, text="Protocol:").grid(row=0, column=0, padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="gbn")
        ttk.Radiobutton(
            config_frame, text="Go-Back-N", variable=self.protocol_var, value="gbn"
        ).grid(row=0, column=1)
        ttk.Radiobutton(
            config_frame,
            text="Selective Repeat",
            variable=self.protocol_var,
            value="sr",
        ).grid(row=0, column=2)

        # Parameters
        ttk.Label(config_frame, text="Window Size:").grid(row=0, column=3, padx=5)
        self.window_entry = ttk.Entry(config_frame, width=5)
        self.window_entry.insert(0, "4")
        self.window_entry.grid(row=0, column=4)

        ttk.Label(config_frame, text="Timeout (s):").grid(row=0, column=5, padx=5)
        self.timeout_entry = ttk.Entry(config_frame, width=5)
        self.timeout_entry.insert(0, "1.0")
        self.timeout_entry.grid(row=0, column=6)

        ttk.Label(config_frame, text="Loss Rate:").grid(row=1, column=0, padx=5)
        self.loss_entry = ttk.Entry(config_frame, width=5)
        self.loss_entry.insert(0, "0.1")
        self.loss_entry.grid(row=1, column=1)

        ttk.Label(config_frame, text="Corruption Rate:").grid(row=1, column=2, padx=5)
        self.corruption_entry = ttk.Entry(config_frame, width=5)
        self.corruption_entry.insert(0, "0.0")
        self.corruption_entry.grid(row=1, column=3)

        ttk.Label(config_frame, text="Delay (s):").grid(row=1, column=4, padx=5)
        self.delay_entry = ttk.Entry(config_frame, width=5)
        self.delay_entry.insert(0, "1.0")
        self.delay_entry.grid(row=1, column=5)

        ttk.Label(config_frame, text="Data Size:").grid(row=1, column=6, padx=5)
        self.size_entry = ttk.Entry(config_frame, width=6)
        self.size_entry.insert(0, "5000")
        self.size_entry.grid(row=1, column=7)

        ttk.Label(config_frame, text="Speed:").grid(row=0, column=8, padx=5)
        self.speed_scale = tk.Scale(
            config_frame,
            from_=0.1,
            to=2.0,
            resolution=0.1,
            orient="horizontal",
            length=100,
        )
        self.speed_scale.set(1.0)
        self.speed_scale.grid(row=0, column=9)

        # Buttons
        self.start_btn = ttk.Button(
            config_frame, text="Start", command=self.start_experiment
        )
        self.start_btn.grid(row=1, column=8, padx=10)

        self.stop_btn = ttk.Button(
            config_frame, text="Stop", command=self.stop_experiment, state="disabled"
        )
        self.stop_btn.grid(row=1, column=9, padx=5)

        # Canvas
        self.canvas = tk.Canvas(self.root, bg="white", height=400)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=5)

        # Draw static elements
        self.sender_x = 100
        self.receiver_x = 900
        self.canvas_height = 400

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Logs")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=10, state="disabled"
        )
        self.log_area.pack(fill="both", expand=True)

    def draw_static(self):
        self.canvas.delete("all")
        # Sender
        self.canvas.create_rectangle(
            self.sender_x - 40,
            50,
            self.sender_x + 40,
            350,
            fill="#e0e0e0",
            outline="black",
        )
        self.canvas.create_text(
            self.sender_x, 30, text="Sender", font=("Arial", 12, "bold")
        )

        # Receiver
        self.canvas.create_rectangle(
            self.receiver_x - 40,
            50,
            self.receiver_x + 40,
            350,
            fill="#e0e0e0",
            outline="black",
        )
        self.canvas.create_text(
            self.receiver_x, 30, text="Receiver", font=("Arial", 12, "bold")
        )

    def log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def start_experiment(self):
        if self.running_experiment:
            return

        try:
            protocol = self.protocol_var.get()
            window_size = int(self.window_entry.get())
            timeout = float(self.timeout_entry.get())
            loss = float(self.loss_entry.get())
            corruption = float(self.corruption_entry.get())
            delay = float(self.delay_entry.get())
            data_size = int(self.size_entry.get())
            speed = self.speed_scale.get()

            # Adjust for speed (Slower speed = Higher delay/timeout)
            # Speed 1.0 = Normal
            # Speed 0.5 = 2x Slower (2x Delay)
            # Speed 2.0 = 2x Faster (0.5x Delay)
            if speed > 0:
                delay = delay / speed
                timeout = timeout / speed

        except ValueError:
            self.log("Error: Invalid parameters")
            return

        self.running_experiment = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.draw_static()
        self.animations = []

        # Run in thread
        threading.Thread(
            target=self._run_simulation,
            args=(protocol, window_size, timeout, loss, corruption, delay, data_size),
            daemon=True,
        ).start()

    def stop_experiment(self):
        if self.sender:
            self.sender.stop()
        if self.receiver:
            self.receiver.stop()
        self.running_experiment = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        # Clear animations and queue
        self.animations.clear()
        with self.event_queue.mutex:
            self.event_queue.queue.clear()

        # Redraw static to clear canvas of moving items
        self.draw_static()

        self.log("Experiment stopped.")

    def _run_simulation(
        self, protocol, window_size, timeout, loss, corruption, delay, data_size
    ):
        self.log(f"Starting {protocol.upper()} simulation...")

        # Create channels with observer
        # Note: We use the SAME observer for both channels to simplify UI handling
        forward_channel = UnreliableChannel(
            loss, corruption, delay, 0.0, observer=self.observer
        )
        backward_channel = UnreliableChannel(
            loss, corruption, delay, 0.0, observer=self.observer
        )

        # Queues
        # We create the queues manually to wire them up
        # Sender -> forward_channel -> receiver_queue -> Receiver
        # Receiver -> backward_channel -> sender_queue -> Sender

        # But wait, my previous wiring logic in CLI was a bit messy.
        # Let's do it cleanly.

        # 1. Create queues that the CHANNELS will write to.
        receiver_input_queue = (
            queue.Queue()
        )  # Forward channel writes here, Receiver reads here
        sender_input_queue = (
            queue.Queue()
        )  # Backward channel writes here, Sender reads here

        if protocol == "gbn":
            # Receiver reads from receiver_input_queue
            # Receiver writes to backward_channel (which writes to sender_input_queue)
            self.receiver = GBNReceiver(
                backward_channel, sender_input_queue, observer=self.observer
            )
            # Hack: GBNReceiver creates its own receiver_queue. We need to replace it or feed it.
            # Actually, GBNReceiver reads from self.receiver_queue.
            # So we should tell forward_channel to write to self.receiver.receiver_queue!

            # Sender reads from sender_input_queue (no, Sender creates self.sender_queue)
            # So we tell backward_channel to write to self.sender.sender_queue!

            # Let's instantiate first.
            # We pass dummy queues to init because we will wire up channels correctly.

            # Receiver needs `sender_queue` (where it sends ACKs).
            # Sender needs `receiver_queue` (where it sends Data).

            # But `channel.send(packet, destination_queue)` takes the destination queue.

            # So:
            # 1. Create Receiver. It has `self.receiver_queue`.
            # 2. Create Sender. It has `self.sender_queue`.
            # 3. Sender needs to know `receiver.receiver_queue` to pass to forward_channel?
            #    No, Sender calls `self.channel.send(packet, self.receiver_queue)`.
            #    So we pass `receiver.receiver_queue` to Sender constructor.

            # 4. Receiver needs to know `sender.sender_queue` to pass to backward_channel?
            #    No, Receiver calls `self.channel.send(ack, self.sender_queue)`.
            #    So we pass `sender.sender_queue` to Receiver constructor.

            # Circular dependency again.
            # Solution: Create one, then the other, then update.

            # Create Receiver with dummy sender queue
            dummy_q = queue.Queue()
            self.receiver = GBNReceiver(
                backward_channel, dummy_q, observer=self.observer
            )

            # Create Sender with receiver's queue
            self.sender = GBNSender(
                forward_channel,
                self.receiver.receiver_queue,
                window_size,
                timeout,
                observer=self.observer,
            )

            # Update Receiver's sender queue
            self.receiver.sender_queue = self.sender.sender_queue

        elif protocol == "sr":
            dummy_q = queue.Queue()
            self.receiver = SRReceiver(
                backward_channel, dummy_q, window_size, observer=self.observer
            )
            self.sender = SRSender(
                forward_channel,
                self.receiver.receiver_queue,
                window_size,
                timeout,
                observer=self.observer,
            )
            self.receiver.sender_queue = self.sender.sender_queue

        # Start threads
        self.receiver.start()
        self.sender.start()

        # Send data
        data = "".join(random.choices(string.ascii_letters, k=data_size)).encode()
        self.sender.send_data(data)

        # Monitor completion
        while self.running_experiment:
            if len(self.receiver.get_received_data()) >= len(data):
                self.log("Transfer Complete!")
                break
            time.sleep(0.5)

        self.stop_experiment()

    def _start_ui_loop(self):
        self._process_events()
        self._animate()
        self.root.after(20, self._start_ui_loop)

    def _process_events(self):
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                type = event[0]

                if type == "LOG":
                    self.log(event[1])
                elif type == "SENT":
                    # ('SENT', packet, delay, start_time)
                    packet, delay, start_time = event[1], event[2], event[3]
                    is_ack = packet.flags & Packet.ACK

                    # Create animation object
                    start_x = self.receiver_x if is_ack else self.sender_x
                    end_x = self.sender_x if is_ack else self.receiver_x

                    # Visual representation
                    color = "green" if is_ack else "blue"
                    text = f"ACK{packet.ack_num}" if is_ack else f"SEQ{packet.seq_num}"

                    # Random Y offset to avoid overlap
                    y = (
                        100 + (packet.seq_num % 10) * 20
                        if not is_ack
                        else 100 + (packet.ack_num % 10) * 20
                    )

                    item_id = self.canvas.create_text(
                        start_x, y, text=text, fill=color, font=("Arial", 10, "bold")
                    )

                    anim = {
                        "id": item_id,
                        "start_time": start_time,
                        "end_time": start_time + delay,
                        "start_x": start_x,
                        "end_x": end_x,
                        "y": y,
                        "packet": packet,
                        "status": "transit",
                    }
                    self.animations.append(anim)

                elif type == "LOST":
                    packet = event[1]
                    # Find the animation for this packet and mark it lost
                    for anim in self.animations:
                        if anim["packet"] == packet and anim["status"] == "transit":
                            anim["status"] = "lost"
                            self.canvas.itemconfig(anim["id"], fill="red")
                            break

                elif type == "CORRUPT":
                    packet = event[1]
                    for anim in self.animations:
                        if anim["packet"] == packet and anim["status"] == "transit":
                            anim["status"] = "corrupt"
                            self.canvas.itemconfig(anim["id"], fill="orange")
                            break

                elif type == "DELIVERED":
                    packet = event[1]
                    # Animation will finish naturally, but we can flash it or remove it
                    pass

            except queue.Empty:
                break

    def _animate(self):
        current_time = time.time()
        to_remove = []

        for anim in self.animations:
            if anim["status"] == "lost":
                # Fade out or just stop
                # For simplicity, let's just remove it after a bit
                if (
                    current_time > anim["end_time"]
                ):  # Lost packets "disappear" when they would have arrived
                    self.canvas.delete(anim["id"])
                    to_remove.append(anim)
                continue

            progress = (current_time - anim["start_time"]) / (
                anim["end_time"] - anim["start_time"]
            )

            if progress >= 1.0:
                # Arrived
                self.canvas.delete(anim["id"])
                to_remove.append(anim)
            else:
                # Move
                new_x = anim["start_x"] + (anim["end_x"] - anim["start_x"]) * progress
                self.canvas.coords(anim["id"], new_x, anim["y"])

        for anim in to_remove:
            self.animations.remove(anim)


if __name__ == "__main__":
    root = tk.Tk()
    app = RDTApp(root)
    root.mainloop()
