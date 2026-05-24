import socket
import threading
import json
from datetime import datetime

class Node:
    def __init__(self, host='0.0.0.0', port=18444):
        self.host = host
        self.port = port
        self.peers = []
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(10)
        while self.running:
            try:
                conn, addr = s.accept()
                threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()
            except:
                break

    def _handle(self, conn, addr):
        try:
            data = conn.recv(4096).decode()
            if data:
                msg = json.loads(data)
                if msg.get('type') == 'ping':
                    conn.send(json.dumps({'type': 'pong', 'time': datetime.now().isoformat()}).encode())
        except:
            pass
        finally:
            conn.close()

    def connect_to_peer(self, host, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.send(json.dumps({'type': 'ping'}).encode())
            resp = s.recv(4096).decode()
            if resp:
                self.peers.append({'host': host, 'port': port})
            s.close()
        except:
            pass

    def broadcast(self, data):
        for peer in self.peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((peer['host'], peer['port']))
                s.send(json.dumps(data).encode())
                s.close()
            except:
                pass

    def stop(self):
        self.running = False
