 File Sharing System using Python Sockets and PySide2

This project is a cross-platform **File Sharing System** implemented in Python using **socket programming** and **PySide2** for the graphical user interface. It allows clients to connect to a server, view available files, upload, download, and delete files in real-time with support for multiple clients and large files.



## Features

GUI for both **Client** and **Server** using `PySide2`.
Upload, Download, and Delete files from the server.
Real-time file listing using JSON-based communication.
Efficient file transfer using 64KB chunked sockets.
Multi-threaded server to support concurrent clients.
Disk space check before accepting uploads.
Transfer speed and progress reporting for large files.

