from concurrent.futures import thread
from email import message
from pydoc import cli
import socket
import threading
import os
import json
import time

class ServerSocket:
    
    def __init__(self, DATA_PATH = 'data'):
        self.DATA_PATH = DATA_PATH
        self.CHUNK_SIZE = 65536  # 64KB chunks for faster transfer (increased from 8KB)
        self.TIMEOUT = 300  # 5 minutes timeout for large file transfers
    
    def start_server(self, HOST = socket.gethostbyname(socket.gethostname()), PORT = 3458):
        self.HOST = HOST
        self.PORT = PORT
        self.ADDR = (self.HOST, self.PORT)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Socket optimizations for speed
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
        
        self.server.bind(self.ADDR)
        print('==> STARTING SERVER...')
        self.server.listen()
        print(f'==> SERVER LISTENING ON: {self.HOST}:{self.PORT}')

        while True:
            client, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client, addr))
            thread.start()

    def handle_client(self, client, addr):
        print("==> CONNECTED TO:", addr)
        try:
            # Optimize client socket for speed
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
            client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
            client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
            
            self.send_message(client, self.getFileContents())
            while True:
                data = self.recv_message(client)
                action = data['action']
                filename = data['filename']
                filepath = os.path.join(self.DATA_PATH, filename)
                if action == 'download':
                    thread = threading.Thread(target=self.send_file, args=(client, filepath))
                    thread.start()
                elif action == 'delete':
                    os.remove(filepath)
                    message = json.dumps({'message' :'SUCCESS'})
                    self.send_message(client, message)
                elif action == 'upload':
                    message = json.dumps({'message' :'READY FOR UPLOAD'})
                    self.send_message(client, message)
                    self.recv_file(client, filepath)
        except Exception as e:
            print(f"==> ERROR with client {addr}: {e}")
        finally:
            client.close()

    def send_file(self, client, filepath):
        print("==> SENDING:", filepath)
        
        try:
            # Set timeout for large file transfers
            client.settimeout(self.TIMEOUT)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            # Send file size first
            client.sendall(file_size.to_bytes(8, 'big'))
            
            # Send file in chunks with optimized transfer
            with open(filepath, 'rb') as f:
                bytes_sent = 0
                start_time = time.time()
                
                while bytes_sent < file_size:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    client.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    # Print progress and speed for large files
                    if file_size > 1024 * 1024:  # Only for files > 1MB
                        if bytes_sent % (5 * 1024 * 1024) < self.CHUNK_SIZE:  # Print every 5MB
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                speed = (bytes_sent / (1024*1024)) / elapsed_time  # MB/s
                                progress = (bytes_sent / file_size) * 100
                                print(f"==> Progress: {progress:.1f}% ({bytes_sent / (1024*1024):.1f}MB / {file_size / (1024*1024):.1f}MB) - Speed: {speed:.1f}MB/s")
            
            total_time = time.time() - start_time
            avg_speed = (file_size / (1024*1024)) / total_time if total_time > 0 else 0
            print(f"==> Sent successfully in {total_time:.1f}s - Avg Speed: {avg_speed:.1f}MB/s")
        except Exception as e:
            print(f"==> ERROR sending file: {e}")
            raise

    def recv_file(self, client, filename):
        print("==> RECEIVING FILE...")
        
        try:
            # Set timeout for large file transfers
            client.settimeout(self.TIMEOUT)
            
            # Receive file size first
            expected_size = b""
            while len(expected_size) < 8:
                more_size = client.recv(8 - len(expected_size))
                if not more_size:
                    raise Exception("Short file length received")
                expected_size += more_size

            expected_size = int.from_bytes(expected_size, 'big')
            print(f"==> Expected file size: {expected_size / (1024*1024):.1f}MB")

            # Check available disk space
            free_space = self.get_free_disk_space()
            if expected_size > free_space:
                raise Exception(f"Insufficient disk space. Need {expected_size / (1024*1024):.1f}MB, have {free_space / (1024*1024):.1f}MB")

            # Receive file in chunks with optimized transfer
            bytes_received = 0
            start_time = time.time()
            
            with open(filename, 'wb') as f:
                while bytes_received < expected_size:
                    chunk_size = min(self.CHUNK_SIZE, expected_size - bytes_received)
                    chunk = client.recv(chunk_size)
                    if not chunk:
                        raise Exception("Incomplete file received")
                    f.write(chunk)
                    bytes_received += len(chunk)
                    
                    # Print progress and speed for large files
                    if expected_size > 1024 * 1024:  # Only for files > 1MB
                        if bytes_received % (5 * 1024 * 1024) < self.CHUNK_SIZE:  # Print every 5MB
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                speed = (bytes_received / (1024*1024)) / elapsed_time  # MB/s
                                progress = (bytes_received / expected_size) * 100
                                print(f"==> Progress: {progress:.1f}% ({bytes_received / (1024*1024):.1f}MB / {expected_size / (1024*1024):.1f}MB) - Speed: {speed:.1f}MB/s")
            
            total_time = time.time() - start_time
            avg_speed = (expected_size / (1024*1024)) / total_time if total_time > 0 else 0
            print(f"==> FILE RECEIVED: {filename} in {total_time:.1f}s - Avg Speed: {avg_speed:.1f}MB/s")
        except Exception as e:
            print(f"==> ERROR receiving file: {e}")
            # Clean up partial file if it exists
            if os.path.exists(filename):
                os.remove(filename)
            raise
    
    def get_free_disk_space(self):
        """Get free disk space in bytes"""
        try:
            statvfs = os.statvfs(self.DATA_PATH)
            return statvfs.f_frsize * statvfs.f_bavail
        except:
            # Fallback for Windows
            import shutil
            return shutil.disk_usage(self.DATA_PATH).free
    
    def send_message(self, client, message):
        print("==> SENDING MESSAGE...")
        client.sendall(message.encode('utf-8'))
        print("==> MESSAGE SENT")

    def recv_message(self, client):
        print("==> RECEIVING MESSAGE...")
        data = client.recv(1024).decode('utf-8')
        data = json.loads(data)
        print("==> MESSAGE RECEIVED")
        return data

    def close(self):
        self.server.close()

    def getFileContents(self):
        files = os.listdir(self.DATA_PATH)
        return json.dumps(files)


if __name__=='__main__':
    serverSocket = ServerSocket()

