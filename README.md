# Reliable Data Transfer (RDT) Visualizer

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Status](https://img.shields.io/badge/status-stable-green)

A comprehensive Python implementation of Reliable Data Transfer protocols, featuring **Go-Back-N (GBN)** and **Selective Repeat (SR)**. This project provides a hands-on simulation environment to understand how reliable communication is achieved over an unreliable channel, handling packet loss, corruption, delay, and reordering.

## 🚀 Features

- **Protocol Implementation**: Full implementation of Go-Back-N and Selective Repeat protocols.
- **Unreliable Channel Simulation**: Configurable packet loss, corruption, delay, and reordering.
- **Interactive GUI**: Tkinter-based visualization to watch packets and ACKs in real-time.
- **CLI Benchmarking**: Command-line interface for running performance benchmarks.
- **Socket Support**: Run Sender and Receiver as separate processes communicating via UDP sockets.
- **Configurable Parameters**: Adjust window size, timeout, loss rate, corruption rate, and more.

## 📂 Project Structure

```shell
RDT-Visualizer/
├── src/
│   ├── packet.py          # Packet structure and checksum logic
│   ├── channel.py         # Unreliable channel simulator
│   ├── rdt_base.py        # Base classes for Sender and Receiver
│   ├── gbn.py             # Go-Back-N implementation
│   ├── sr.py              # Selective Repeat implementation
│   ├── cli.py             # CLI entry point
│   ├── ui.py              # GUI application
│   ├── udp_sender.py      # UDP Socket Sender
│   ├── udp_receiver.py    # UDP Socket Receiver
│   ├── udp_proxy.py       # UDP Channel Proxy
│   └── utils.py           # Utility functions
├── README.md              # Project documentation
└── requirements.txt       # Dependencies (Standard Library only)
```

## 🛠️ Installation

No external dependencies are required. The project uses Python's standard library.

1. **Clone the repository**:

   ```bash
   git clone https://github.com/SharafatKarim/RDT-Visualizer
   cd RDT-SelectiveRepeat-vs-GoBackN
   ```

2. **Ensure Python 3.8+ is installed**:

   ```bash
   python3 --version
   ```

## 🖥️ Usage

### 1. Graphical User Interface (GUI)

The easiest way to explore the protocols is using the visualization tool.

```bash
python3 -m src.ui
```

- **Protocol**: Choose between GBN and SR.
- **Parameters**: Set Window Size, Timeout, Loss Rate, etc.
- **Speed**: Adjust simulation speed using the slider.
- **Start**: Begin the simulation and watch packets flow.

### 2. Command Line Interface (CLI)

Run benchmarks to compare throughput and reliability.

```bash
# Run Go-Back-N with 10% packet loss
python3 -m src.cli --protocol gbn --size 10000 --loss 0.1

# Run Selective Repeat with corruption and delay
python3 -m src.cli --protocol sr --size 10000 --corruption 0.05 --delay 0.1
```

## 📊 Protocols Overview

| Feature | Go-Back-N (GBN) | Selective Repeat (SR) |
| :--- | :--- | :--- |
| **Sender Window** | Size $N$ | Size $N$ |
| **Receiver Window** | Size 1 | Size $N$ |
| **ACK Type** | Cumulative | Individual |
| **Retransmission** | All packets from timeout base | Only missing packets |
| **Complexity** | Low | High (Buffering required) |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
