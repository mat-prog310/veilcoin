import json
import os
from datetime import datetime

class PeerManager:
    def __init__(self, data_dir='data'):
        self.peers = []
        self.data_dir = data_dir
        self.peers_file = os.path.join(data_dir, 'peers.json')
        self.load()

    def load(self):
        if os.path.exists(self.peers_file):
            with open(self.peers_file) as f:
                self.peers = json.load(f)

    def save(self):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.peers_file, 'w') as f:
            json.dump(self.peers, f, indent=2)

    def add_peer(self, host, port):
        peer = {'host': host, 'port': port, 'added': datetime.now().isoformat()}
        if peer not in self.peers:
            self.peers.append(peer)
            self.save()

    def remove_peer(self, host, port):
        self.peers = [p for p in self.peers if not (p['host'] == host and p['port'] == port)]
        self.save()

    def get_peers(self):
        return self.peers
