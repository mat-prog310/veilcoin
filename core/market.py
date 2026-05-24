import json, os
from datetime import datetime

class VeilMarket:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.current_price = 0.0001
        self.circulating_supply = 0
        self.total_volume_24h = 0
        self.trades = []
        self.data_path = "data/market.json"
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path) as f:
                d = json.load(f)
                self.current_price = d.get('current_price', 0.0001)
                self.circulating_supply = d.get('circulating_supply', 0)
                self.total_volume_24h = d.get('total_volume_24h', 0)
                self.trades = d.get('trades', [])

    def save(self):
        os.makedirs('data', exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({'current_price': self.current_price, 'circulating_supply': self.circulating_supply, 'total_volume_24h': self.total_volume_24h, 'trades': self.trades[-100:]}, f, indent=2)

    def get_stats(self):
        return {'current_price': self.current_price, 'circulating_supply': self.circulating_supply, 'volume_24h': self.total_volume_24h}
