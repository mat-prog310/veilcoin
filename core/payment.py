import json, os
from datetime import datetime

class LiquidityPool:
    def __init__(self, market, blockchain):
        self.market = market; self.blockchain = blockchain
        self.sell_offers = {}; self.swaps = []
        self.max_price_change_percent = 10
        self.min_veil_per_trade = 1; self.max_veil_per_trade = 1000
        self.price_history = []
        self.data_path = "data/market.json"
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path) as f:
                d = json.load(f)
                self.sell_offers = d.get('sell_offers', {})
                self.swaps = d.get('swaps', [])
                self.price_history = d.get('price_history', [])

    def save(self):
        os.makedirs('data', exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({'sell_offers': self.sell_offers, 'swaps': self.swaps[-100:], 'price_history': self.price_history[-100:]}, f, indent=2)

    def get_veil_price(self):
        if self.price_history: return sum(self.price_history[-10:]) / len(self.price_history[-10:])
        return 0.0001

    def get_reference_price(self):
        if len(self.price_history) >= 10: return sum(self.price_history[-10:]) / 10
        return self.get_veil_price()

    def is_price_allowed(self, price):
        ref = self.get_reference_price()
        mx = ref * (1 + self.max_price_change_percent / 100)
        mn = ref * (1 - self.max_price_change_percent / 100)
        if price > mx: return False, mx
        if price < mn: return False, mn
        return True, price

    def add_liquidity_from_mining(self, addr, amount): pass

    def create_sell_offer(self, wallet_name, veil_amount, price_per_veil, paypal_email):
        from web.routes import active_wallets
        if veil_amount < self.min_veil_per_trade or veil_amount > self.max_veil_per_trade:
            return {'success': False, 'error': f'Entre {self.min_veil_per_trade} et {self.max_veil_per_trade} VEIL'}
        ok, lim = self.is_price_allowed(price_per_veil)
        if not ok: return {'success': False, 'error': f'Prix hors limites. Max: {lim:.8f}€'}
        if wallet_name not in active_wallets: return {'success': False, 'error': 'Wallet non connecté'}
        w = active_wallets[wallet_name]
        if w.balance < veil_amount: return {'success': False, 'error': 'Solde insuffisant'}
        oid = f"OFFER-{int(datetime.now().timestamp())}"
        w.balance -= veil_amount; w.save()
        self.sell_offers[oid] = {'offer_id': oid, 'seller_wallet': wallet_name, 'seller_address': w.address[:20]+'...',
            'veil_amount': veil_amount, 'price_per_veil': price_per_veil, 'total_eur': veil_amount * price_per_veil,
            'seller_paypal': paypal_email, 'status': 'open', 'buyer_wallet': None, 'buyer_paypal': None,
            'created_at': datetime.now().isoformat()}
        self.save()
        return {'success': True, 'offer_id': oid, 'veil_amount': veil_amount, 'total_eur': veil_amount * price_per_veil}

    def buyer_lock_funds(self, oid, buyer_wallet, buyer_paypal):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'open':
            return {'success': False, 'error': 'Offre indisponible'}
        o = self.sell_offers[oid]
        o['status'] = 'buyer_locked'; o['buyer_wallet'] = buyer_wallet
        o['buyer_paypal'] = buyer_paypal; o['buyer_locked_at'] = datetime.now().isoformat()
        self.save()
        return {'success': True, 'total_eur': o['total_eur'], 'veil_amount': o['veil_amount']}

    def seller_accept_buyer(self, oid, seller_wallet):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'buyer_locked':
            return {'success': False, 'error': 'Action impossible'}
        o = self.sell_offers[oid]
        if o['seller_wallet'] != seller_wallet: return {'success': False, 'error': 'Pas votre annonce'}
        o['status'] = 'both_locked'; o['revealed_at'] = datetime.now().isoformat()
        self.save()
        return {'success': True, 'emails_revealed': True, 'seller_paypal': o['seller_paypal'],
                'buyer_paypal': o['buyer_paypal'], 'total_eur': o['total_eur'], 'veil_amount': o['veil_amount']}

    def confirm_payment(self, oid, wallet):
        if oid not in self.sell_offers or self.sell_offers[oid]['status'] != 'both_locked':
            return {'success': False, 'error': 'Action impossible'}
        o = self.sell_offers[oid]
        from web.routes import active_wallets
        if o['buyer_wallet'] in active_wallets:
            active_wallets[o['buyer_wallet']].balance += o['veil_amount']
            active_wallets[o['buyer_wallet']].save()
        self.price_history.append(o['price_per_veil'])
        o['status'] = 'completed'; o['completed_at'] = datetime.now().isoformat()
        self.swaps.append({'offer_id': oid, 'seller': o['seller_wallet'][:20], 'buyer': o['buyer_wallet'][:20],
                          'veil': o['veil_amount'], 'eur': o['total_eur'], 'timestamp': datetime.now().isoformat()})
        self.save()
        return {'success': True, 'message': f'{o["veil_amount"]} VEIL → Acheteur !'}

    def cancel_offer(self, oid, wallet):
        if oid not in self.sell_offers: return {'success': False, 'error': 'Offre non trouvée'}
        o = self.sell_offers[oid]
        if o['seller_wallet'] != wallet and o.get('buyer_wallet') != wallet:
            return {'success': False, 'error': 'Pas autorisé'}
        from web.routes import active_wallets
        if o['seller_wallet'] in active_wallets:
            active_wallets[o['seller_wallet']].balance += o['veil_amount']
            active_wallets[o['seller_wallet']].save()
        o['status'] = 'cancelled'; self.save()
        return {'success': True, 'message': 'VEIL remboursés'}

    def get_open_offers(self):
        ref = self.get_reference_price()
        return [{'offer_id': oid, 'seller': o['seller_address'], 'veil_amount': o['veil_amount'],
                 'price_per_veil': o['price_per_veil'], 'total_eur': o['total_eur'], 'status': o['status'],
                 'created_at': o['created_at'],
                 'deviation': round(((o['price_per_veil'] - ref) / ref) * 100, 2)}
                for oid, o in self.sell_offers.items() if o['status'] in ['open', 'buyer_locked']]

    def get_pool_info(self):
        return {'open_offers': len([o for o in self.sell_offers.values() if o['status'] in ['open', 'buyer_locked']]),
                'total_swaps': len(self.swaps), 'veil_price': self.get_veil_price(),
                'reference_price': self.get_reference_price(), 'max_change': f'±{self.max_price_change_percent}%'}

    def get_swap_history(self, limit=50): return self.swaps[-limit:]
