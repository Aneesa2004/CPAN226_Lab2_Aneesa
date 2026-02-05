# This program was modified by Aneesa / n01745842

import socket  # IMPROVEMENT: use UDP socket for receiving packets
import argparse  # IMPROVEMENT: read command-line arguments for port/output
import struct  # IMPROVEMENT: unpack sequence numbers and build ACKs
import os  # IMPROVEMENT: used to create unique filenames if needed

EOF_SEQ = 0xFFFFFFFF  # IMPROVEMENT: special sequence number to signal EOF reliably

def make_output_filename(base_output, addr):  # IMPROVEMENT: choose correct output filename based on lab requirements
    ip, sender_port = addr  # IMPROVEMENT: extract sender IP and port for uniqueness if needed
    if base_output and base_output != "received_file.jpg":  # IMPROVEMENT: if user provided --output, respect it
        return base_output  # IMPROVEMENT: use the exact output filename requested (received_direct/received_relay)
    return f"received_{ip.replace('.', '_')}_{sender_port}.jpg"  # IMPROVEMENT: fallback to unique auto-name

def run_server(port, output_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IMPROVEMENT: create UDP socket for server

    server_address = ('', port)  # IMPROVEMENT: bind on all interfaces for the specified port
    print(f"[*] Server listening on port {port}")  # IMPROVEMENT: show server is running
    print(f"[*] Output file argument: {output_file}")  # IMPROVEMENT: confirm output argument is being used
    sock.bind(server_address)  # IMPROVEMENT: start listening on the port

    expected_seq = 0  # IMPROVEMENT: track the next expected packet number for in-order delivery
    buffer = {}  # IMPROVEMENT: store out-of-order packets until they can be written

    try:
        while True:
            f = None  # IMPROVEMENT: file handle for current transfer
            filename = None  # IMPROVEMENT: actual filename being written this transfer

            while True:
                data, addr = sock.recvfrom(4096)  # IMPROVEMENT: receive packet (header + payload) from UDP

                if not data:  # IMPROVEMENT: ignore empty datagrams (we use EOF_SEQ instead)
                    continue  # IMPROVEMENT: skip empty packet

                if len(data) < 4:  # IMPROVEMENT: ensure packet is at least 4 bytes for seq header
                    continue  # IMPROVEMENT: ignore invalid packet

                seq_num = struct.unpack('!I', data[:4])[0]  # IMPROVEMENT: read sequence number from header
                payload = data[4:]  # IMPROVEMENT: payload is everything after the 4-byte header

                ack = struct.pack('!I', seq_num)  # IMPROVEMENT: build ACK containing the received sequence number
                for _ in range(3):  # IMPROVEMENT: send ACK multiple times to reduce effect of loss/reorder
                    sock.sendto(ack, addr)  # IMPROVEMENT: send ACK to sender

                if f is None and seq_num != EOF_SEQ and len(payload) > 0:  # IMPROVEMENT: open output file on first real data
                    print("==== Start of reception ====")  # IMPROVEMENT: mark transfer start
                    filename = make_output_filename(output_file, addr)  # IMPROVEMENT: respect --output if provided
                    f = open(filename, 'wb')  # IMPROVEMENT: open output file for writing bytes
                    print(f"[*] File opened as '{filename}' from sender {addr}.")  # IMPROVEMENT: log chosen filename

                if seq_num == EOF_SEQ:  # IMPROVEMENT: handle reliable EOF marker
                    print(f"[*] Reliable EOF received from {addr}. Flushing buffer and closing.")  # IMPROVEMENT: EOF log
                    if f is not None:  # IMPROVEMENT: only flush if file was opened
                        while expected_seq in buffer:  # IMPROVEMENT: write any buffered packets that are now in order
                            f.write(buffer.pop(expected_seq))  # IMPROVEMENT: write buffered data in correct order
                            expected_seq += 1  # IMPROVEMENT: advance expected sequence
                    break  # IMPROVEMENT: end this transfer

                if len(payload) == 0:  # IMPROVEMENT: ignore header-only packets that are not EOF
                    continue  # IMPROVEMENT: skip empty payload

                if seq_num == expected_seq:  # IMPROVEMENT: if this is the next expected packet
                    f.write(payload)  # IMPROVEMENT: write payload immediately in correct order
                    expected_seq += 1  # IMPROVEMENT: increment expected sequence after writing

                    while expected_seq in buffer:  # IMPROVEMENT: flush any packets that became in-order
                        f.write(buffer.pop(expected_seq))  # IMPROVEMENT: write buffered packet
                        expected_seq += 1  # IMPROVEMENT: advance expected sequence

                elif seq_num > expected_seq:  # IMPROVEMENT: packet arrived early (out of order)
                    buffer[seq_num] = payload  # IMPROVEMENT: store payload in buffer for later writing

                else:
                    pass  # IMPROVEMENT: ignore duplicate/old packet already written

            if f:  # IMPROVEMENT: close output file after transfer completes
                f.close()  # IMPROVEMENT: ensure file is properly closed so image can open
            expected_seq = 0  # IMPROVEMENT: reset expected sequence for next transfer
            buffer.clear()  # IMPROVEMENT: clear buffer for next transfer
            print("==== End of reception ====")  # IMPROVEMENT: mark transfer end

    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")  # IMPROVEMENT: graceful stop message
    except Exception as e:
        print(f"[!] Error: {e}")  # IMPROVEMENT: show server error if something breaks
    finally:
        sock.close()  # IMPROVEMENT: close socket when done
        print("[*] Server socket closed.")  # IMPROVEMENT: confirm socket shutdown

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver")  # IMPROVEMENT: create argument parser
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")  # IMPROVEMENT: set listening port
    parser.add_argument("--output", type=str, default="received_file.jpg", help="Output file name")  # IMPROVEMENT: output filename
    args = parser.parse_args()  # IMPROVEMENT: parse args from command line

    run_server(args.port, args.output)  # IMPROVEMENT: start the server with given args
