

import os
import socket
import threading
import json
import time

class ClientSocket():

    def __init__(self, DATA_PATH = 'downloads'):
        self.DATA_PATH = DATA_PATH
        self.CHUNK_SIZE = 65536  # 64KB chunks for faster transfer (increased from 8KB)
        self.TIMEOUT = 300  # 5 minutes timeout for large file transfers

    def connectToServer(self, HOST = socket.gethostbyname(socket.gethostname()), PORT = 3458):
        self.HOST = HOST
        self.PORT = PORT
        self.ADDR = (HOST, PORT)
        print(f'==> CONNECTING TO: {self.HOST}:{self.PORT}')
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Socket optimizations for speed
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
        
        self.client.connect(self.ADDR)
        print("==> CONNECTED\n==> RECEIVING FILE LIST...")
        return self.recv_message()

    def recv_file(self, filename):
        try:
            # Set timeout for large file transfers
            self.client.settimeout(self.TIMEOUT)
            
            # Receive file size first
            expected_size = b""
            while len(expected_size) < 8:
                more_size = self.client.recv(8 - len(expected_size))
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
                    chunk = self.client.recv(chunk_size)
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
            print(f"==> File received successfully in {total_time:.1f}s - Avg Speed: {avg_speed:.1f}MB/s")
        except Exception as e:
            print(f"==> ERROR receiving file: {e}")
            # Clean up partial file if it exists
            if os.path.exists(filename):
                os.remove(filename)
            raise

    def send_file(self, filepath):
        print("==> SENDING:", filepath)
        
        try:
            # Set timeout for large file transfers
            self.client.settimeout(self.TIMEOUT)
            
            # Get file size
            file_size = os.path.getsize(filepath)
            print(f"==> File size: {file_size / (1024*1024):.1f}MB")
            
            # Send file size first
            self.client.sendall(file_size.to_bytes(8, 'big'))
            
            # Send file in chunks with optimized transfer
            with open(filepath, 'rb') as f:
                bytes_sent = 0
                start_time = time.time()
                
                while bytes_sent < file_size:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    self.client.sendall(chunk)
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
    
    def get_free_disk_space(self):
        """Get free disk space in bytes"""
        try:
            statvfs = os.statvfs(self.DATA_PATH)
            return statvfs.f_frsize * statvfs.f_bavail
        except:
            # Fallback for Windows
            import shutil
            return shutil.disk_usage(self.DATA_PATH).free
    
    def send_message(self, message):
        print("==> SENDING MESSAGE...")
        self.client.sendall(message.encode('utf-8'))
        print("==> MESSAGE SENT")

    def recv_message(self):
        print("==> RECEIVING MESSAGE...")
        data = self.client.recv(1024).decode('utf-8')
        data = json.loads(data)
        print("==> MESSAGE RECEIVED")
        return data
    
    def close(self):
        self.client.close()

if __name__=='__main__':
    clientSocket = ClientSocket()
    clientSocket.connectToServer()