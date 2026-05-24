import json
import os
from datetime import datetime

class LiquidityPool:
    def __init__(self, market, blockchain):
        self.market = market
        self.blockchain = blockchain
        self.sell_offers = {}
        self.swaps = []
        self.max_price_change_percent = 10
        self.min_veil_per_trade = 1
        self.max_veil_per_trade = 1000
        self.price_history = []
        self.data_path = "data/market.json"
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                d = json.load(f)
                self.sell_offers = d.get('sell_offers', {})
                self.swaps = d.get('swaps', [])
                self.price_history = d.get('price_history', [])

    def save(self):
        os.makedirs('data', exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({'sell_offers': self.sell_offers, 'swaps': self.swaps[-100:], 'price_history': self.price_history[-100:]}, f, indent=2)

    def get_veil_price(self):
        if self.price_history:
            return sum(self.price_history[-10:]) / len(self.price_history[-10:])
        prices = [o['price_per_veil'] for o in self.sell_offers.values() if o['status'] == 'open']
        return sum(prices) / len(prices) if prices else 0.0001

    def get_reference_price(self):
        return sum(self.price_history[-10:]) / len(self.price_history[-10:]) if len(self.price_history) >= 10 else (sum(self.price_history) / len(self.price_history) if self.price_history else 0.0001)

    def is_price_allowed(self, price):
        ref = self.get_reference_price()
        max_p = ref * (1 + self.max_price_change_percent / 100)
        min_p = ref * (1 - self.max_price_change_percent / 100)
        return (False, max_p) if price > max_p else ((False, min_p) if price < min_p else (True, price))

    def add_liquidity_from_mining(self, miner_address, veil_amount):
        pass

    def create_sell_offer(self, wallet_name, veil_amount, price_per_veil, paypal_email):
        from web.routes import active_wallets
        if veil_amount < self.min_veil_per_trade or veil_amount > self.max_veil_per_trade:
            return {'success': False, 'error': f'Quantité entre {self.min_veil_per_trade} et {self.max_veil_per_trade} VEIL'}
        allowed, limit = self.is_price_allowed(price_per_veil)
        if not allowed:
            return {'success': False, 'error': f'Prix trop éloigné du marché. Max: {limit:.8f}€/VEIL'}
        if wallet_name not in active_wallets:
            return {'success': False, 'error': 'Wallet non connecté'}
        w = active_wallets[wallet_name]
        if w.balance < veil_amount:
            return {'success': False, 'error': 'Solde insuffisant'}
        oid = f"OFFER-{int(datetime.now().timestamp())}"
        w.balance -= veil_amount
        w.save()
        self.sell_offers[oid] = {'offer_id': oid, 'seller_wallet': wallet_name, 'seller_address': w.address[:20]+'...', 'veil_amount': veil_amount, 'price_per_veil': price_per_veil, 'total_eur': veil_amount * price_per_veil, 'seller_paypal': paypal_email, 'status': 'open', 'buyer_wallet': None, 'buyer_paypal': None, 'created_at': datetime.now().isoformat()}
        self.save()
        return {'success': True, 'offer_id': oid, 'veil_amount': veil_amount, 'total_eur': veil_amount * price_per_veil}

    def buyer_lock_funds(self, oid, buyer_wallet, buyer_paypal):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'open':
            return {'success': False, 'error': 'Offre indisponible'}
        self.sell_offers[oid].update({'status': 'buyer_locked', 'buyer_wallet': buyer_wallet, 'buyer_paypal': buyer_paypal, 'buyer_locked_at': datetime.now().isoformat()})
        self.save()
        return {'success': True, 'total_eur': self.sell_offers[oid]['total_eur'], 'veil_amount': self.sell_offers[oid]['veil_amount']}

    def seller_accept_buyer(self, oid, seller_wallet):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'buyer_locked' or self.sell_offers[oid]['seller_wallet'] != seller_wallet:
            return {'success': False, 'error': 'Action impossible'}
        o = self.sell_offers[oid]
        o['status'] = 'both_locked'
        o['revealed_at'] = datetime.now().isoformat()
        self.save()
        return {'success': True, 'emails_revealed': True, 'seller_paypal': o['seller_paypal'], 'buyer_paypal': o['buyer_paypal'], 'total_eur': o['total_eur'], 'veil_amount': o['veil_amount']}

    def confirm_payment(self, oid, wallet):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'both_locked':
            return {'success': False, 'error': 'Action impossible'}
        o = self.sell_offers[oid]
        from web.routes import active_wallets
        if o['buyer_wallet'] in active_wallets:
            active_wallets[o['buyer_wallet']].balance += o['veil_amount']
            active_wallets[o['buyer_wallet']].save()
        self.price_history.append(o['price_per_veil'])
        o['status'] = 'completed'
        o['completed_at'] = datetime.now().isoformat()
        self.swaps.append({'offer_id': oid, 'seller': o['seller_wallet'][:20], 'buyer': o['buyer_wallet'][:20], 'veil': o['veil_amount'], 'eur': o['total_eur'], 'timestamp': datetime.now().isoformat()})
        self.save()
        return {'success': True, 'message': f'{o["veil_amount"]} VEIL → Acheteur !'}

    def cancel_offer(self, oid, wallet):
        if oid not in self.sell_offers:
            return {'success': False, 'error': 'Offre non trouvée'}
        o = self.sell_offers[oid]
        if o['seller_wallet'] != wallet and o.get('buyer_wallet') != wallet:
            return {'success': False, 'error': 'Pas autorisé'}
        from web.routes import active_wallets
        if o['seller_wallet'] in active_wallets:
            active_wallets[o['seller_wallet']].balance += o['veil_amount']
            active_wallets[o['seller_wallet']].save()
        o['status'] = 'cancelled'
        self.save()
        return {'success': True, 'message': 'VEIL remboursés'}

    def get_open_offers(self):
        ref = self.get_reference_price()
        return [{'offer_id': oid, 'seller': o['seller_address'], 'veil_amount': o['veil_amount'], 'price_per_veil': o['price_per_veil'], 'total_eur': o['total_eur'], 'status': o['status'], 'created_at': o['created_at'], 'deviation': round(((o['price_per_veil'] - ref) / ref) * 100, 2)} for oid, o in self.sell_offers.items() if o['status'] in ['open', 'buyer_locked']]

    def get_pool_info(self):
        return {'open_offers': len([o for o in self.sell_offers.values() if o['status'] in ['open', 'buyer_locked']]), 'total_swaps': len(self.swaps), 'veil_price': self.get_veil_price(), 'reference_price': self.get_reference_price(), 'max_change': f'±{self.max_price_change_percent}%', 'limits': f'{self.min_veil_per_trade}-{self.max_veil_per_trade} VEIL/trade'}

    def get_swap_history(self, limit=50):
        return self.swaps[-limit:]
