"""
Marché P2P VeilCoin - Achat et Vente avec PayPal réel
Emails cachés jusqu'au double blocage
"""
import json, os
from datetime import datetime

class LiquidityPool:
    
    def __init__(self, market, blockchain):
        self.market = market
        self.blockchain = blockchain
        
        self.sell_offers = {}  # Offres de vente (je vends mes VEIL)
        self.buy_offers = {}   # Offres d'achat (je veux acheter des VEIL)
        self.swaps = []
        
        # Protection
        self.max_price_change_percent = 10
        self.min_veil_per_trade = 1
        self.max_veil_per_trade = 1000
        self.price_history = []
        
        self.data_path = "data/market.json"
        self.load()
    
      def load(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path) as f:
                    d = json.load(f)
                    self.sell_offers = d.get('sell_offers', {})
                    self.buy_offers = d.get('buy_offers', {})
                    self.swaps = d.get('swaps', [])
                    self.price_history = d.get('price_history', [])
                print(f"📊 Marché chargé: {len(self.sell_offers)} offres vente, {len(self.buy_offers)} offres achat, {len(self.swaps)} swaps")
            except Exception as e:
                print(f"⚠️ Erreur chargement marché: {e}")
        else:
            print("📊 Nouveau marché créé")

    def save(self):
        os.makedirs('data', exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({
                'sell_offers': self.sell_offers,
                'buy_offers': self.buy_offers,
                'swaps': self.swaps[-100:],
                'price_history': self.price_history[-100:]
            }, f, indent=2)

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

    # ==================== OFFRES DE VENTE (Je vends mes VEIL) ====================

    def create_sell_offer(self, wallet_name, veil_amount, price_per_veil, paypal_email):
        from web.routes import active_wallets
        if veil_amount < self.min_veil_per_trade or veil_amount > self.max_veil_per_trade:
            return {'success': False, 'error': f'Entre {self.min_veil_per_trade} et {self.max_veil_per_trade} VEIL'}
        ok, lim = self.is_price_allowed(price_per_veil)
        if not ok: return {'success': False, 'error': f'Prix hors limites. Max: {lim:.8f}€'}
        if wallet_name not in active_wallets: return {'success': False, 'error': 'Wallet non connecté'}
        w = active_wallets[wallet_name]
        if w.balance < veil_amount: return {'success': False, 'error': 'Solde insuffisant'}
        
        oid = f"SELL-{int(datetime.now().timestamp())}"
        w.balance -= veil_amount; w.save()
        
        self.sell_offers[oid] = {
            'offer_id': oid, 'type': 'sell',
            'seller_wallet': wallet_name, 'seller_address': w.address[:20]+'...',
            'veil_amount': veil_amount, 'price_per_veil': price_per_veil,
            'total_eur': veil_amount * price_per_veil,
            'seller_paypal': paypal_email, 'status': 'open',
            'buyer_wallet': None, 'buyer_paypal': None,
            'created_at': datetime.now().isoformat()
        }
        self.save()
        return {'success': True, 'offer_id': oid, 'veil_amount': veil_amount, 'total_eur': veil_amount * price_per_veil}

    # ==================== OFFRES D'ACHAT (Je veux acheter des VEIL) ====================

    def create_buy_offer(self, wallet_name, veil_wanted, price_per_veil, paypal_email):
        from web.routes import active_wallets
        if veil_wanted < self.min_veil_per_trade or veil_wanted > self.max_veil_per_trade:
            return {'success': False, 'error': f'Entre {self.min_veil_per_trade} et {self.max_veil_per_trade} VEIL'}
        ok, lim = self.is_price_allowed(price_per_veil)
        if not ok: return {'success': False, 'error': f'Prix hors limites. Max: {lim:.8f}€'}
        if wallet_name not in active_wallets: return {'success': False, 'error': 'Wallet non connecté'}
        
        oid = f"BUY-{int(datetime.now().timestamp())}"
        
        self.buy_offers[oid] = {
            'offer_id': oid, 'type': 'buy',
            'buyer_wallet': wallet_name, 'buyer_address': active_wallets[wallet_name].address[:20]+'...',
            'veil_wanted': veil_wanted, 'price_per_veil': price_per_veil,
            'total_eur': veil_wanted * price_per_veil,
            'buyer_paypal': paypal_email, 'status': 'open',
            'seller_wallet': None, 'seller_paypal': None,
            'created_at': datetime.now().isoformat()
        }
        self.save()
        return {'success': True, 'offer_id': oid, 'veil_wanted': veil_wanted, 'total_eur': veil_wanted * price_per_veil}

    # ==================== ACCEPTER UNE OFFRE DE VENTE (J'achète) ====================

    def buyer_lock_funds(self, offer_id, buyer_wallet, buyer_paypal):
        if offer_id not in self.sell_offers: return {'success': False, 'error': 'Offre non trouvée'}
        o = self.sell_offers[offer_id]
        if o['status'] != 'open': return {'success': False, 'error': 'Offre déjà réservée'}
        o['status'] = 'buyer_locked'
        o['buyer_wallet'] = buyer_wallet
        o['buyer_paypal'] = buyer_paypal
        o['buyer_locked_at'] = datetime.now().isoformat()
        self.save()
        return {'success': True, 'total_eur': o['total_eur'], 'veil_amount': o['veil_amount']}

    def seller_accept_buyer(self, offer_id, seller_wallet):
        """Le vendeur accepte → emails révélés"""
        if offer_id not in self.sell_offers: return {'success': False, 'error': 'Offre non trouvée'}
        o = self.sell_offers[offer_id]
        if o['status'] != 'buyer_locked': return {'success': False, 'error': 'Pas d\'acheteur en attente'}
        if o['seller_wallet'] != seller_wallet: return {'success': False, 'error': 'Pas votre annonce'}
        o['status'] = 'both_locked'
        o['revealed_at'] = datetime.now().isoformat()
        self.save()
        return {
            'success': True, 'emails_revealed': True,
            'seller_paypal': o['seller_paypal'], 'buyer_paypal': o['buyer_paypal'],
            'total_eur': o['total_eur'], 'veil_amount': o['veil_amount']
        }

    # ==================== ACCEPTER UNE OFFRE D'ACHAT (Je vends) ====================

    def seller_lock_veil(self, offer_id, seller_wallet):
        """Un vendeur accepte une offre d'achat → ses VEIL sont bloqués"""
        if offer_id not in self.buy_offers: return {'success': False, 'error': 'Offre non trouvée'}
        o = self.buy_offers[offer_id]
        if o['status'] != 'open': return {'success': False, 'error': 'Offre déjà réservée'}
        
        from web.routes import active_wallets
        if seller_wallet not in active_wallets: return {'success': False, 'error': 'Wallet non connecté'}
        w = active_wallets[seller_wallet]
        if w.balance < o['veil_wanted']: return {'success': False, 'error': 'Solde insuffisant'}
        
        w.balance -= o['veil_wanted']; w.save()
        
        o['status'] = 'seller_locked'
        o['seller_wallet'] = seller_wallet
        o['seller_locked_at'] = datetime.now().isoformat()
        self.save()
        return {'success': True, 'total_eur': o['total_eur'], 'veil_amount': o['veil_wanted']}

    def buyer_accept_seller(self, offer_id, buyer_wallet, buyer_paypal):
        """L'acheteur confirme → emails révélés"""
        if offer_id not in self.buy_offers: return {'success': False, 'error': 'Offre non trouvée'}
        o = self.buy_offers[offer_id]
        if o['status'] != 'seller_locked': return {'success': False, 'error': 'Pas de vendeur en attente'}
        if o['buyer_wallet'] != buyer_wallet: return {'success': False, 'error': 'Pas votre annonce'}
        o['status'] = 'both_locked'
        o['buyer_paypal'] = buyer_paypal
        o['revealed_at'] = datetime.now().isoformat()
        self.save()
        return {
            'success': True, 'emails_revealed': True,
            'seller_paypal': o.get('seller_paypal', 'À demander au vendeur'),
            'buyer_paypal': buyer_paypal,
            'total_eur': o['total_eur'], 'veil_amount': o['veil_wanted']
        }

    # ==================== CONFIRMER PAIEMENT ====================

    def confirm_payment(self, offer_id, wallet):
        """Confirmer le paiement → VEIL libérés"""
        # Chercher dans les 2 types d'offres
        o = self.sell_offers.get(offer_id) or self.buy_offers.get(offer_id)
        if not o: return {'success': False, 'error': 'Offre non trouvée'}
        if o['status'] != 'both_locked': return {'success': False, 'error': 'Emails non révélés'}
        
        from web.routes import active_wallets
        
        if o['type'] == 'sell':
            # Offre de vente : donner VEIL à l'acheteur
            if o['buyer_wallet'] in active_wallets:
                active_wallets[o['buyer_wallet']].balance += o['veil_amount']
                active_wallets[o['buyer_wallet']].save()
        else:
            # Offre d'achat : donner VEIL à l'acheteur
            if o['buyer_wallet'] in active_wallets:
                active_wallets[o['buyer_wallet']].balance += o['veil_wanted']
                active_wallets[o['buyer_wallet']].save()
        
        self.price_history.append(o['price_per_veil'])
        o['status'] = 'completed'
        o['completed_at'] = datetime.now().isoformat()
        
        self.swaps.append({
            'offer_id': offer_id, 'type': o['type'],
            'seller': o.get('seller_wallet', '')[:20],
            'buyer': o.get('buyer_wallet', '')[:20],
            'veil': o.get('veil_amount', o.get('veil_wanted', 0)),
            'eur': o['total_eur'],
            'timestamp': datetime.now().isoformat()
        })
        self.save()
        return {'success': True, 'message': '✅ Transaction terminée ! VEIL transférés.'}

    # ==================== ANNULER ====================

    def cancel_offer(self, offer_id, wallet):
        o = self.sell_offers.get(offer_id) or self.buy_offers.get(offer_id)
        if not o: return {'success': False, 'error': 'Offre non trouvée'}
        if o.get('seller_wallet') != wallet and o.get('buyer_wallet') != wallet:
            return {'success': False, 'error': 'Pas autorisé'}
        
        from web.routes import active_wallets
        
        if o['type'] == 'sell' and o.get('seller_wallet') in active_wallets:
            active_wallets[o['seller_wallet']].balance += o['veil_amount']
            active_wallets[o['seller_wallet']].save()
        elif o['type'] == 'buy' and o.get('seller_wallet') in active_wallets:
            active_wallets[o['seller_wallet']].balance += o['veil_wanted']
            active_wallets[o['seller_wallet']].save()
        
        o['status'] = 'cancelled'; self.save()
        return {'success': True, 'message': 'VEIL remboursés'}

    # ==================== GETTERS ====================

    def get_open_sell_offers(self):
        ref = self.get_reference_price()
        return [{
            'offer_id': oid, 'seller': o['seller_address'],
            'veil_amount': o['veil_amount'], 'price_per_veil': o['price_per_veil'],
            'total_eur': o['total_eur'], 'status': o['status'],
            'deviation': round(((o['price_per_veil'] - ref) / ref) * 100, 2),
            'created_at': str(o['created_at'])
        } for oid, o in self.sell_offers.items() if o['status'] in ['open', 'buyer_locked']]

    def get_open_buy_offers(self):
        ref = self.get_reference_price()
        return [{
            'offer_id': oid, 'buyer': o['buyer_address'],
            'veil_wanted': o['veil_wanted'], 'price_per_veil': o['price_per_veil'],
            'total_eur': o['total_eur'], 'status': o['status'],
            'deviation': round(((o['price_per_veil'] - ref) / ref) * 100, 2),
            'created_at': str(o['created_at'])
        } for oid, o in self.buy_offers.items() if o['status'] in ['open', 'seller_locked']]

    def get_pool_info(self):
        return {
            'open_sell_offers': len([o for o in self.sell_offers.values() if o['status'] in ['open', 'buyer_locked']]),
            'open_buy_offers': len([o for o in self.buy_offers.values() if o['status'] in ['open', 'seller_locked']]),
            'total_swaps': len(self.swaps),
            'veil_price': self.get_veil_price(),
            'reference_price': self.get_reference_price()
        }

    def get_swap_history(self, limit=50): return self.swaps[-limit:]
