# sockets.py

def recv_exact(sock, n: int) -> bytes:
    """Receive exactly n bytes from a TCP socket or raise ConnectionError."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("socket closed while reading")
        data += chunk
    return data
