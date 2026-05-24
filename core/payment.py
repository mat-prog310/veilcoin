"""
Marché P2P VeilCoin - Pool + Trésorerie auto
50% du burn paie les serveurs (7€/mois Render Pro)
"""
import json, os
from datetime import datetime

class LiquidityPool:
    def __init__(self, market, blockchain):
        self.market = market
        self.blockchain = blockchain
        
        # Pool
        self.pool_veil = 0.0
        self.pool_eur = 0.0
        
        # Trésorerie
        self.treasury_veil = 0.0
        self.treasury_eur = 0.0
        self.server_cost_eur = 7.00  # Render Pro
        self.burn_to_treasury_percent = 0.50  # 50% burn → trésorerie
        
        # P2P
        self.sell_offers = {}
        self.buy_offers = {}
        self.swaps = []
        self.max_price_change_percent = 10
        self.min_veil_per_trade = 1
        self.max_veil_per_trade = 1000
        self.price_history = []
        
        self.data_path = "data/market.json"
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path) as f:
                d = json.load(f)
                self.pool_veil = d.get('pool_veil', 0)
                self.pool_eur = d.get('pool_eur', 0)
                self.treasury_veil = d.get('treasury_veil', 0)
                self.treasury_eur = d.get('treasury_eur', 0)
                self.sell_offers = d.get('sell_offers', {})
                self.buy_offers = d.get('buy_offers', {})
                self.swaps = d.get('swaps', [])
                self.price_history = d.get('price_history', [])
        else:
            self.save()

    def save(self):
        os.makedirs('data', exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({
                'pool_veil': self.pool_veil,
                'pool_eur': self.pool_eur,
                'treasury_veil': self.treasury_veil,
                'treasury_eur': self.treasury_eur,
                'sell_offers': self.sell_offers,
                'buy_offers': self.buy_offers,
                'swaps': self.swaps[-100:],
                'price_history': self.price_history[-100:]
            }, f, indent=2)

    def get_veil_price(self):
        if self.pool_veil > 0 and self.pool_eur > 0:
            return self.pool_eur / self.pool_veil
        return 0.001

    def add_liquidity_from_mining(self, miner_address, veil_amount):
        self.pool_veil += veil_amount
        self.pool_eur += veil_amount * 0.001
        self.market.current_price = self.get_veil_price()
        self.save()

    def pay_server_bill(self):
        if self.treasury_eur >= self.server_cost_eur:
            return {
                'can_pay': True,
                'treasury_eur': self.treasury_eur,
                'server_cost': self.server_cost_eur,
                'remaining': self.treasury_eur - self.server_cost_eur,
                'months_covered': int(self.treasury_eur // self.server_cost_eur)
            }
        return {
            'can_pay': False,
            'treasury_eur': self.treasury_eur,
            'server_cost': self.server_cost_eur,
            'missing': round(self.server_cost_eur - self.treasury_eur, 2),
            'missing_veil': round((self.server_cost_eur - self.treasury_eur) / self.get_veil_price(), 2) if self.get_veil_price() > 0 else 0
        }

    def get_open_sell_offers(self):
        return [{'offer_id': oid, 'seller': o['seller_address'], 'veil_amount': o['veil_amount'],
                 'price_per_veil': o['price_per_veil'], 'total_eur': o['total_eur'], 'status': o['status']}
                for oid, o in self.sell_offers.items() if o['status'] in ['open', 'buyer_locked']]

    def get_open_buy_offers(self):
        return [{'offer_id': oid, 'buyer': o['buyer_address'], 'veil_wanted': o['veil_wanted'],
                 'price_per_veil': o['price_per_veil'], 'total_eur': o['total_eur'], 'status': o['status']}
                for oid, o in self.buy_offers.items() if o['status'] in ['open', 'seller_locked']]

    def get_pool_info(self):
        return {
            'pool_veil': self.pool_veil,
            'pool_eur': self.pool_eur,
            'veil_price': self.get_veil_price(),
            'total_swaps': len(self.swaps),
            'treasury_veil': self.treasury_veil,
            'treasury_eur': self.treasury_eur,
            'server_cost': self.server_cost_eur,
            'can_pay': self.pay_server_bill()['can_pay']
        }

    def get_swap_history(self, limit=50):
        return self.swaps[-limit:]
