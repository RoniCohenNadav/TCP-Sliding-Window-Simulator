import socket


# function to set the message either from a file or user input
def settingMsg():
    choice = input("enter 1 to read from a file or 2 to write the message (if you want to end write in the message exit): ").strip().lower()
    if choice == "1":
        file_path = input("enter the file path: ")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.startswith("message:"): # check if the line contains the message
                        ans = line[9:-2]  # extract the message content
                if ans is None:
                    raise ValueError("No message in file.")
                return ans
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading settings from file: {e}. Please enter the settings manually.")

    # if the user chooses to write manually
    message = input("enter the message: ")
    return message

# function to configure settings such as window size and timeout
def settingsVal():
    choice = input("enter 1 to read from a file or 2 to enter the details by yourself: ").strip().lower()
    if choice == "1":
        file_path = input("enter the file path: ")
        settings = {"window_size": None, "timeout": None}
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if not line.startswith("message:") and ":" in line: # Skip lines starting with "message:" and parse settings
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        if key in settings:
                            settings[key] = int(value)
                if None in settings.values():
                    raise ValueError("Some settings are missing in the file.")
                return settings.values()
        except (FileNotFoundError, ValueError) as e:
            print(f"Error reading settings from file: {e} please enter the settings manually.")

    # If file reading fails or user chooses not to use a file
    window_size = int(input("enter the sliding window size: "))
    timeout = int(input("enter the timeout in seconds: "))
    return window_size, timeout

# function to receive ACKs from the server
def receive_acks(client_socket, segments, next_ack, window_size,timeout, window_end, next_to_send):
    client_socket.settimeout(timeout)  # Set timeout for receiving ACK
    while True:
        try:
            ack = client_socket.recv(1024).decode()
            ack_segments = ack.split("ACK ")[1:]
            ack_segments = [segment.strip() for segment in ack_segments]  # filter empty values if any

            for a in ack_segments:
                ack_segment = int(a.split()[-1])  # extract segment number
                print(f"received ACK: {ack_segment}")
                next_ack = ack_segment+1

                if window_end < len(segments) - 1:
                    window_end = min(next_ack + window_size - 1, len(segments) - 1)
                    while next_to_send <= window_end:  # if we have segment in the window that we don't send
                        index, segment = segments[next_to_send]
                        print(f"Sending new segment {index}: {segment}")
                        client_socket.sendall(f"{index}:{segment}".encode())  # send the segment
                        client_socket.settimeout(timeout)  # reset the timeout for receiving ACKs
                        next_to_send += 1

            # Exit if all segments are acknowledged
            if next_ack >= len(segments):
                print("All segments have been sent and the server receive")
                client_socket.sendall("-1".encode())  # notify the server - complete
                return next_ack,next_to_send

        except socket.timeout:
            print(f"Timeout occurred while waiting for ACK. Exiting receive_acks.")
            break

        except Exception as e:
            print(f"Error while receiving ACK: {e}")
            break

    print(f"Exiting receive_acks with next_to_send={next_ack}")
    return next_ack,next_to_send

# sliding window implementation to send the message in segments
def sliding_window(client_socket, message, max_msg_size, window_size, timeout):
    segments = []  # Split the message into segments based on the maximum size
    for i in range(0, len(message), max_msg_size):
        segment_index = i // max_msg_size
        segment = message[i:i + max_msg_size]
        if len(segment) < max_msg_size:
            segment = segment.ljust(max_msg_size, " ")  #If the length of the segment is less than the defined maximum size
        formatted_index = str(segment_index).zfill(7)  # header- 7 digits
        segments.append((formatted_index, segment))  # Store segment index and data
    print(f"Message split into {len(segments)} segments: {segments}")

    next_ack = 0  # Start with the first segment
    next_to_send = 0
    while next_ack < len(segments):
        window_end = min(next_ack + window_size, len(segments))
        for i in range(next_ack, window_end):  # send all segments in the current window
            index, segment = segments[i]
            client_socket.sendall(f"{index}:{segment}".encode())
            next_to_send += 1
            print(f"Sending segment {int(index)}: {segment}")

        next_ack,next_to_send = receive_acks(client_socket, segments, next_ack, window_size,timeout, window_end, next_to_send)

def sliding_window_lose2(client_socket, message, max_msg_size, window_size, timeout):
    segments = []  # Split the message into segments based on the maximum size
    for i in range(0, len(message), max_msg_size):
        segment_index = i // max_msg_size
        segment = message[i:i + max_msg_size]
        if len(segment) < max_msg_size:
            segment = segment.ljust(max_msg_size,
                                    " ")  # If the length of the segment is less than the defined maximum size
        formatted_index = str(segment_index).zfill(7)  # header- 7 digits
        segments.append((formatted_index, segment))  # Store segment index and data
    print(f"Message split into {len(segments)} segments: {segments}")

    next_ack = 0  # Start with the first segment
    missing_segment_index = 2  # Index of the segment to simulate loss
    next_to_send = 0
    while next_to_send < len(segments):
        window_end = min(next_ack + window_size, len(segments))
        for i in range(next_to_send, window_end):  # send all segments in the current window
            index, segment = segments[i]
            if int(index) == missing_segment_index:  # Skip sending the missing segment
                print(f"Skipping segment {int(index)} to simulate loss.")
            else:
                client_socket.sendall(f"{index}:{segment}".encode())
                next_to_send += 1
                print(f"Sending segment {int(index)}: {segment}")

        # After sending the window, send the missing segment
        if missing_segment_index >= next_ack and missing_segment_index < window_end:
            index, segment = segments[missing_segment_index]
            print(f"Sending missing segment {int(index)}: {segment}")
            client_socket.sendall(f"{index}:{segment}".encode())
            next_to_send += 1

        next_ack,next_to_send = receive_acks(client_socket, segments, next_ack, window_size, timeout, window_end,next_to_send)


# function to run the client
def run_client():
    host = 'localhost'
    port = 12345
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print(f"Connected to server at {host}:{port}")

    max_msg_size = int(client_socket.recv(1024).decode()) # receive the max size message from the server
    print(f"maximum message size allowed by server: {max_msg_size} bytes.")

    # Get settings and send timeout to the server
    window_size, timeout = settingsVal()
    print(f"server allows messages up to {max_msg_size} bytes, sliding window size of {window_size}, timeout of {timeout} seconds.")

    while True:
        message = settingMsg()

        if message.strip().lower() == "exit":
            # Exit the client when user inputs "exit"
            client_socket.send("exit".encode())
            ans = client_socket.recv(1024).decode()
            if ans.strip().lower() == "exit":
                print("Server acknowledged exit. Closing connection.")
            break
        sliding_window(client_socket, message, max_msg_size, window_size, timeout)# send the message using the sliding window protocol
        #sliding_window_lose2(client_socket, message, max_msg_size, window_size, timeout) # check for sending segments in the wrong order

    client_socket.close()
    print("Connection closed.")


if __name__ == "__main__":
    run_client()
