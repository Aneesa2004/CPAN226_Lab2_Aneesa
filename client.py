# This program was modified by Aneesa / n01745842

import socket
import argparse
import os
import struct  # IMPROVEMENT: pack/unpack sequence numbers
import time    # IMPROVEMENT: small delays to help relay flush buffers

EOF_SEQ = 0xFFFFFFFF              # IMPROVEMENT: reliable EOF marker
CHUNK_SIZE = 4092                 # IMPROVEMENT: 4092 data + 4 header = 4096 max
TIMEOUT_SECONDS = 0.35             # IMPROVEMENT: faster retransmits under loss
MAX_RETRIES = 5000                # IMPROVEMENT: prevent infinite waiting if network is too lossy

def wait_for_ack(sock, expected_ack):
    retries = 0  # IMPROVEMENT: count retries to avoid infinite loops
    while True:
        if retries >= MAX_RETRIES:
            raise RuntimeError(f"Too many retries waiting for ACK {expected_ack}")  # IMPROVEMENT: fail safely

        try:
            data, _ = sock.recvfrom(4096)  # IMPROVEMENT: read whatever arrives
            if len(data) != 4:
                continue  # IMPROVEMENT: ignore non-ACK packets
            ack_num = struct.unpack('!I', data)[0]  # IMPROVEMENT: decode ACK number
            if ack_num == expected_ack:
                return True  # IMPROVEMENT: correct ACK received
        except socket.timeout:
            retries += 1  # IMPROVEMENT: timeout counts as a retry
            return False  # IMPROVEMENT: signal caller to retransmit

def run_client(target_ip, target_port, input_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (target_ip, target_port)

    sock.settimeout(TIMEOUT_SECONDS)  # IMPROVEMENT: timeout enables retransmits

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    seq_num = 0  # IMPROVEMENT: sequence number starts at 0

    try:
        with open(input_file, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                packet = struct.pack('!I', seq_num) + chunk  # IMPROVEMENT: prepend sequence header

                while True:
                    sock.sendto(packet, server_address)
                    if wait_for_ack(sock, seq_num):
                        break  # IMPROVEMENT: move on once ACK received

                seq_num += 1  # IMPROVEMENT: next packet

        eof_packet = struct.pack('!I', EOF_SEQ)  # IMPROVEMENT: reliable EOF packet (header-only)

        while True:
            sock.sendto(eof_packet, server_address)
            if wait_for_ack(sock, EOF_SEQ):
                break  # IMPROVEMENT: EOF acknowledged

        for _ in range(10):
            sock.sendto(eof_packet, server_address)  # IMPROVEMENT: extra EOF sends help with relay buffering
            time.sleep(0.05)  # IMPROVEMENT: short delay to allow relay flush

        print("[*] File transmission complete.")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1")
    parser.add_argument("--target_port", type=int, default=12000)
    parser.add_argument("--file", type=str, required=True)
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)

