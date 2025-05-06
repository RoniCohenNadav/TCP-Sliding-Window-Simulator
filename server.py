import socket
import time
def settingM():
    choice = input("enter 1 to load the max_message_size from a file or 2 to enter it by yourself :").strip().lower()
    if choice == "1":
        file_path = input("enter the file path: ")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.startswith("maximum_msg_size:"):
                        value = int(line[17:-1])
                if value is None:
                    raise ValueError("Some settings are missing in the file.")
                return value
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading settings from file: {e}. Please enter the settings manually.")

    # If file reading fails or user chooses not to use a file
    max_message_size = int(input("Enter the maximum message size (in bytes): "))
    return max_message_size

def run_server(host='localhost', port=12345):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Server is listening on {host}:{port}")

    con, adr = server_socket.accept()
    print(f"Connection established with {adr}")

    max_size = settingM()
    con.sendall(f"{max_size}".encode())  # Send max_size to the client
    print(f"Maximum message size ({max_size} bytes) sent to the client.")

    received_segments = {}  # Store received segments by index
    expected_segment = 0    # Expected segment to complete the sequence
    while True:
        try:
            data = con.recv(max_size+8).decode()  # Receive data from the client

            if not data:
                print("No data received.")
                break

            if data.strip().lower() == "exit":
                print("Exit command received. Closing connection.")
                break

            if data == "-1":  # the client signals that all segments have been received
                print("Client finished sending segments-resetting server for the next message.")
                # Reset server state to prepare for the next message
                received_segments = {}
                expected_segment = 0
                continue

            if ":" not in data:
                print(f"Invalid message format received: {data}")
                continue

            index, segment = data.split(":", 1)
            index = int(index)
            if index not in received_segments: # check if the segment is already in the received_segments
                received_segments[index] = segment
                print(f"Adding segment {index} to the received segments.")

                while expected_segment in received_segments:  # update the last index in the sequence
                    expected_segment += 1

                #time.sleep(3)  #tomeOut check
                con.send(f"ACK {expected_segment-1}".encode())  # send ACK for each segment received
                print(f"Sending ACK for segment {expected_segment-1}")

        except Exception as e:
            print(f"Error occurred: {e}")
            break

    con.close()
    server_socket.close()
    print("Server shut down.")


if __name__ == "__main__":
    run_server()
