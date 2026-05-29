# web/blueprint.py
from flask import Blueprint, jsonify, request, render_template
import sys, os
import hashlib
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wallet import VeilWallet
from core.market import VeilMarket
from core.payment import LiquidityPool
from config import Config
import base64

web_bp = Blueprint('web', __name__, template_folder='../templates')

# ==================== P2P ESCROW ====================
p2p_orders = {}
p2p_counter = 0

# ==================== ANTI-DUMP ====================
MAX_TRADE_PERCENT = 5
MIN_TRADE_INTERVAL = 60
COOLDOWN_BLOCKS = 10
user_last_trade = {}
user_trade_count = {}

# ==================== INITIALISATION ====================
try:
    from core.blockchain import Blockchain
    blockchain = Blockchain()
except:
    blockchain = None
    print("⚠️ Blockchain non disponible")

market = VeilMarket(blockchain) if blockchain else None
pool = LiquidityPool(market, blockchain) if market else None

if pool:
    pool.pool_veil = 1000000
    pool.pool_eur = 10000
else:
    class DummyPool:
        def __init__(self):
            self.pool_veil = 1000000
            self.pool_eur = 10000
            self.treasury_veil = 0
        def get_veil_price(self):
            return self.pool_eur / self.pool_veil if self.pool_veil > 0 else 0.01
    pool = DummyPool()

active_wallets = {}
mempool = []

MAX_SUPPLY = 1_000_000_000
total_burned = 0
total_fees_collected = 0

DATA_DIR = Config.DATA_DIR
MINED_BLOCKS_FILE = os.path.join(DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(DATA_DIR, "burn_stats.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ==================== IMPORT DES MODULES APRÈS DATA_DIR ====================
from core.reputation import ReputationSystem
from core.secure_storage import SecureStorage

reputation = ReputationSystem(DATA_DIR)
secure_storage = SecureStorage(DATA_DIR)

# ==================== PERSISTANCE P2P ====================
P2P_ORDERS_FILE = os.path.join(DATA_DIR, "p2p_orders.json")

def load_p2p_orders():
    global p2p_orders, p2p_counter
    if os.path.exists(P2P_ORDERS_FILE):
        try:
            with open(P2P_ORDERS_FILE, 'r') as f:
                data = json.load(f)
                p2p_orders = data.get('orders', {})
                p2p_counter = data.get('counter', 0)
                print(f"📦 Chargé {len(p2p_orders)} offres P2P")
        except Exception as e:
            print(f"Erreur chargement P2P: {e}")
            p2p_orders = {}
            p2p_counter = 0
    else:
        p2p_orders = {}
        p2p_counter = 0
        print("📦 Aucune offre P2P sauvegardée")

def save_p2p_orders():
    try:
        with open(P2P_ORDERS_FILE, 'w') as f:
            json.dump({
                'orders': p2p_orders,
                'counter': p2p_counter
            }, f, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde P2P: {e}")

load_p2p_orders()

# ==================== PRIX BASÉ SUR TRANSACTIONS P2P ====================

def get_current_price():
    """Calcule le prix basé sur les transactions P2P complétées (status 'completed')"""
    completed_orders = [o for o in p2p_orders.values() if o['status'] == 'completed']
    
    if not completed_orders:
        return 0.01
    
    last_10 = completed_orders[-10:]
    total_value = sum(o['total_eur'] for o in last_10)
    total_veil = sum(o['amount_veil'] for o in last_10)
    price = total_value / total_veil if total_veil > 0 else 0.01
    
    return price

# ==================== HISTORIQUE DES PRIX ====================
PRICE_HISTORY_FILE = os.path.join(DATA_DIR, "price_history.json")

if not os.path.exists(PRICE_HISTORY_FILE):
    with open(PRICE_HISTORY_FILE, 'w') as f:
        json.dump([], f)

@web_bp.route('/api/market/price/history', methods=['GET'])
def get_price_history():
    try:
        with open(PRICE_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        return jsonify({'history': history[-50:]})
    except:
        return jsonify({'history': []})

@web_bp.route('/api/market/price/record', methods=['POST'])
def record_price():
    try:
        d = request.get_json()
        price = d.get('price', 0.01)
        with open(PRICE_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        history.append({'price': price, 'time': datetime.now().strftime('%H:%M:%S')})
        if len(history) > 100:
            history = history[-100:]
        with open(PRICE_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== BLOC GENESIS ====================
if not os.path.exists(MINED_BLOCKS_FILE):
    genesis_block = {
        'index': 0, 'timestamp': time.time(), 'transactions': [], 'nonce': 0,
        'previous_hash': '0' * 64, 'hash': hashlib.sha256(b'VEILCOIN_GENESIS').hexdigest(),
        'miner': 'system', 'reward_miner': 0, 'reward_pool': 0, 'difficulty': 5
    }
    with open(MINED_BLOCKS_FILE, 'w') as f:
        json.dump([genesis_block], f, indent=2)

if os.path.exists(BURN_STATS_FILE):
    try:
        with open(BURN_STATS_FILE, 'r') as f:
            burn_data = json.load(f)
            total_burned = burn_data.get('total_burned', 0)
            total_fees_collected = burn_data.get('total_fees_collected', 0)
    except:
        pass

# ==================== FONCTIONS ====================

def save_burn_stats():
    with open(BURN_STATS_FILE, 'w') as f:
        json.dump({
            'total_burned': total_burned,
            'total_fees_collected': total_fees_collected,
            'max_supply': MAX_SUPPLY,
            'last_update': time.time()
        }, f, indent=2)

def calculate_fee(amount):
    return amount * 0.01

def apply_burn(fee):
    global total_burned, total_fees_collected
    burn_amount = fee * 0.5
    treasury_amount = fee * 0.5
    total_burned += burn_amount
    total_fees_collected += fee
    save_burn_stats()
    return {
        'fee': fee, 'burned': burn_amount, 'treasury': treasury_amount,
        'total_burned_since_start': total_burned,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
    }

def check_anti_manipulation(wallet, amount_veil):
    now = time.time()
    if wallet in user_last_trade:
        elapsed = now - user_last_trade[wallet]
        if elapsed < MIN_TRADE_INTERVAL:
            return False, f"Attendez {MIN_TRADE_INTERVAL - elapsed:.0f} secondes"
    max_trade = pool.pool_veil * (MAX_TRADE_PERCENT / 100)
    if amount_veil > max_trade:
        return False, f"Maximum {MAX_TRADE_PERCENT}% de la pool"
    if wallet in user_trade_count and user_trade_count[wallet] >= COOLDOWN_BLOCKS:
        return False, f"Trop de trades. Attendez {COOLDOWN_BLOCKS} blocs"
    return True, "OK"

def update_trade_record(wallet):
    user_last_trade[wallet] = time.time()
    user_trade_count[wallet] = user_trade_count.get(wallet, 0) + 1

def get_blockchain_stats():
    stats = {'height': 0, 'difficulty': 5, 'total_supply': 0, 'total_burned': total_burned,
             'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0,
             'remaining_supply': MAX_SUPPLY - total_burned, 'mempool_size': len(mempool)}
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                stats['height'] = len(json.load(f))
        except:
            pass
    return stats

def get_recent_blocks(n=1000):
    blocks = []
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                all_blocks = json.load(f)
                for b in all_blocks[-n:]:
                    blocks.append({
                        'index': b.get('index', 0),
                        'hash': b.get('hash', '')[:20],
                        'miner': b.get('miner', 'unknown')[:15],
                        'tx_count': len(b.get('transactions', [])),
                        'nonce': b.get('nonce', 0),
                        'timestamp': b.get('timestamp', time.time())
                    })
        except:
            pass
    return blocks

@web_bp.app_template_filter('datetime')
def format_datetime(timestamp):
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")

# ==================== PAGES ====================

@web_bp.route('/')
def index():
    stats = get_blockchain_stats()
    blocks = get_recent_blocks(10)
    return render_template('index.html', stats=stats, blocks=blocks)

@web_bp.route('/wallet')
def wallet_page():
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@web_bp.route('/blockchain')
def blockchain_page():
    blocks = get_recent_blocks(1000)
    stats = get_blockchain_stats()
    return render_template('blockchain.html', blocks=blocks, stats=stats)

@web_bp.route('/market')
def market_page():
    price = pool.get_veil_price() if pool else 0.01
    return render_template('market.html', price=round(price, 4))

@web_bp.route('/p2p')
def p2p_page():
    return render_template('p2p.html')

# ==================== API WALLET ====================

@web_bp.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip()
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        return jsonify({'success': True, 'name': name, 'address': r['address'], 
                       'seed_phrase': r['seed_phrase'], 'balance': r.get('balance', 0)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/wallet/login', methods=['POST'])
def api_login():
    try:
        d = request.get_json()
        name = d.get('name', '').strip()
        seed = d.get('seed_phrase', '').strip()
        w = VeilWallet(name)
        if not w.load_or_create():
            return jsonify({'success': False, 'error': 'Wallet non trouvé'})
        if not w.verify_seed(seed):
            return jsonify({'success': False, 'error': 'Seed incorrecte'})
        active_wallets[name] = w
        return jsonify({'success': True, 'name': name, 'address': w.address, 'balance': w.balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/wallet/<name>/balance')
def api_balance(name):
    try:
        if name in active_wallets:
            w = active_wallets[name]
        else:
            w = VeilWallet(name)
            if not w.load_or_create():
                return jsonify({'balance_veil': 0})
            active_wallets[name] = w
        price = pool.get_veil_price() if pool else 0.01
        return jsonify({'name': name, 'balance_veil': w.balance, 
                       'balance_eur': round(w.balance * price, 6), 'veil_price': price})
    except:
        return jsonify({'balance_veil': 0})

@web_bp.route('/api/wallet/<name>/send', methods=['POST'])
def api_send(name):
    try:
        d = request.get_json()
        to = d.get('to')
        amount = float(d.get('amount', 0))
        
        w = active_wallets.get(name)
        if not w:
            w = VeilWallet(name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[name] = w
        
        fee = calculate_fee(amount)
        total = amount + fee
        
        if w.balance < total:
            return jsonify({'success': False, 'error': 'Solde insuffisant'})
        
        burn_result = apply_burn(fee)
        w.balance -= total
        w.save()
        mempool.append({'from': w.address, 'to': to, 'amount': amount, 'fee': fee})
        
        return jsonify({'success': True, 'new_balance': w.balance, 'fee': fee, 'burned': burn_result['burned']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== API MARCHÉ ====================

@web_bp.route('/api/market/buy', methods=['POST'])
def market_buy():
    try:
        d = request.get_json()
        wallet_name = d.get('wallet')
        eur_amount = float(d.get('eur_amount', 0))
        
        w = active_wallets.get(wallet_name)
        if not w:
            w = VeilWallet(wallet_name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[wallet_name] = w
        
        current_price = pool.get_veil_price()
        veil_amount = eur_amount / current_price
        
        allowed, msg = check_anti_manipulation(wallet_name, veil_amount)
        if not allowed:
            return jsonify({'success': False, 'error': msg})
        
        if veil_amount > pool.pool_veil:
            return jsonify({'success': False, 'error': 'Liquidité insuffisante'})
        
        pool.pool_eur += eur_amount
        pool.pool_veil -= veil_amount
        w.balance += veil_amount
        w.save()
        
        update_trade_record(wallet_name)
        new_price = pool.get_veil_price()
        
        return jsonify({'success': True, 'veil_received': veil_amount, 'eur_spent': eur_amount,
                       'new_balance': w.balance, 'new_price': new_price,
                       'price_change': round(((new_price - current_price) / current_price) * 100, 2)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/market/sell', methods=['POST'])
def market_sell():
    try:
        d = request.get_json()
        wallet_name = d.get('wallet')
        veil_amount = float(d.get('veil_amount', 0))
        
        w = active_wallets.get(wallet_name)
        if not w:
            w = VeilWallet(wallet_name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[wallet_name] = w
        
        if w.balance < veil_amount:
            return jsonify({'success': False, 'error': 'Solde insuffisant'})
        
        current_price = pool.get_veil_price()
        eur_amount = veil_amount * current_price
        
        allowed, msg = check_anti_manipulation(wallet_name, veil_amount)
        if not allowed:
            return jsonify({'success': False, 'error': msg})
        
        if eur_amount > pool.pool_eur:
            return jsonify({'success': False, 'error': 'Pas assez d\'EUR'})
        
        pool.pool_veil += veil_amount
        pool.pool_eur -= eur_amount
        w.balance -= veil_amount
        w.save()
        
        update_trade_record(wallet_name)
        new_price = pool.get_veil_price()
        
        return jsonify({'success': True, 'eur_received': eur_amount, 'veil_sold': veil_amount,
                       'new_balance': w.balance, 'new_price': new_price,
                       'price_change': round(((new_price - current_price) / current_price) * 100, 2)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/market/price')
def api_price():
    price = get_current_price()
    return jsonify({'current_price': price})

# ==================== API MINER ====================

@web_bp.route('/api/miner/submit_block', methods=['POST'])
def submit_block():
    try:
        data = request.get_json()
        wallet = data.get('wallet')
        nonce = data.get('nonce')
        hash_proof = data.get('hash')
        transactions = data.get('transactions', [])
        
        if not hash_proof.startswith('00000'):
            return jsonify({'success': False, 'error': 'Preuve invalide'})
        
        existing_blocks = []
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
        
        last_index = existing_blocks[-1].get('index', 0) if existing_blocks else 0
        
        new_block = {
            'index': last_index + 1,
            'timestamp': time.time(),
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': existing_blocks[-1].get('hash', '0'*64) if existing_blocks else '0'*64,
            'hash': hash_proof,
            'miner': wallet,
            'reward_miner': 50,
            'reward_pool': 0,
            'difficulty': 5
        }
        
        existing_blocks.append(new_block)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks[-100:], f, indent=2)
        
        w = VeilWallet(wallet)
        w.load_or_create()
        w.balance += 50
        w.save()
        active_wallets[wallet] = w
        
        for wk in list(user_trade_count.keys()):
            user_trade_count[wk] = max(0, user_trade_count[wk] - 1)
        
        return jsonify({'success': True, 'reward_miner': 50, 'new_balance': w.balance, 'block_index': new_block['index']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

# ==================== API P2P ====================

@web_bp.route('/api/p2p/create', methods=['POST'])
def p2p_create_order():
    global p2p_counter
    try:
        d = request.get_json()
        wallet_name = d.get('wallet')
        amount_veil = float(d.get('amount_veil', 0))
        price_eur = float(d.get('price_eur', 0))
        seller_email = d.get('seller_email', '')
        
        if not seller_email:
            return jsonify({'success': False, 'error': 'Email PayPal obligatoire pour vendre'})
        
        w = active_wallets.get(wallet_name)
        if not w:
            w = VeilWallet(wallet_name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[wallet_name] = w
        
        if w.balance < amount_veil:
            return jsonify({'success': False, 'error': 'Solde insuffisant'})
        
        w.balance -= amount_veil
        w.save()
        
        p2p_counter += 1
        order_id = f"P2P_{p2p_counter}"
        
        p2p_orders[order_id] = {
            'id': order_id,
            'seller': wallet_name,
            'seller_email': seller_email,
            'amount_veil': amount_veil,
            'price_eur': price_eur,
            'total_eur': amount_veil * price_eur,
            'status': 'open',
            'buyer': None,
            'buyer_email': None,
            'seller_confirmed': False,
            'buyer_confirmed': False,
            'created_at': time.time()
        }
        
        save_p2p_orders()
        return jsonify({'success': True, 'order_id': order_id, 'order': p2p_orders[order_id]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/orders', methods=['GET'])
def p2p_list_orders():
    open_orders = [o for o in p2p_orders.values() if o['status'] == 'open']
    return jsonify({'orders': open_orders, 'count': len(open_orders)})

@web_bp.route('/api/p2p/my-orders', methods=['GET'])
def p2p_my_orders():
    wallet = request.args.get('wallet')
    my_orders = [o for o in p2p_orders.values() if o.get('seller') == wallet]
    return jsonify({'orders': my_orders})

@web_bp.route('/api/p2p/history', methods=['GET'])
def p2p_history():
    completed_orders = [o for o in p2p_orders.values() if o['status'] == 'completed']
    
    anonymized = []
    for o in completed_orders:
        anonymized.append({
            'timestamp': o.get('completed_at', o.get('created_at', time.time())),
            'seller_masked': o.get('seller', '???')[:4] + '...' + o.get('seller', '???')[-2:] if len(o.get('seller', '')) > 6 else 'Vendeur',
            'buyer_masked': o.get('buyer', '???')[:4] + '...' + o.get('buyer', '???')[-2:] if len(o.get('buyer', '')) > 6 else 'Acheteur',
            'amount_veil': o.get('amount_veil', 0),
            'price_eur': o.get('price_eur', 0),
            'total_eur': o.get('total_eur', 0)
        })
    
    anonymized.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify({'transactions': anonymized, 'count': len(anonymized)})

@web_bp.route('/api/p2p/match', methods=['POST'])
def p2p_match_order():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        buyer_name = d.get('buyer')
        buyer_email = d.get('email')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        if order['status'] != 'open':
            return jsonify({'success': False, 'error': 'Offre déjà prise'})
        
        order['buyer'] = buyer_name
        order['buyer_email'] = buyer_email
        order['status'] = 'matched'
        
        save_p2p_orders()
        
        seller_email = order.get('seller_email', 'Email non renseigné')
        
        return jsonify({
            'success': True, 
            'order_id': order_id, 
            'seller_email': seller_email,
            'amount_eur': order['total_eur']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTE PAIEMENT ====================

@web_bp.route('/api/p2p/pay', methods=['POST'])
def p2p_confirm_payment():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        buyer_name = d.get('buyer')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        
        if order['status'] != 'matched' or order['buyer'] != buyer_name:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        order['status'] = 'paid'
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Paiement confirmé, attente validation vendeur'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTE LIBÉRATION ====================

@web_bp.route('/api/p2p/release', methods=['POST'])
def p2p_release_veil():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        seller_name = d.get('seller')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        
        if order['seller'] != seller_name:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        if order['status'] != 'paid':
            return jsonify({'success': False, 'error': 'Le paiement n\'a pas encore été confirmé'})
        
        can_trade, msg = reputation.can_trade(seller_name)
        if not can_trade:
            return jsonify({'success': False, 'error': f'Vendeur suspendu: {msg}'})
        
        buyer_wallet = active_wallets.get(order['buyer'])
        if not buyer_wallet:
            buyer_wallet = VeilWallet(order['buyer'])
            buyer_wallet.load_or_create()
            active_wallets[order['buyer']] = buyer_wallet
        
        seller_wallet = active_wallets.get(order['seller'])
        if not seller_wallet:
            seller_wallet = VeilWallet(order['seller'])
            seller_wallet.load_or_create()
            active_wallets[order['seller']] = seller_wallet
        
        buyer_wallet.balance += order['amount_veil']
        buyer_wallet.save()
        seller_wallet.save()
        
        order['status'] = 'completed'
        order['completed_at'] = time.time()
        save_p2p_orders()
        
        new_price = get_current_price()
        record_price(new_price)
        
        reputation.add_success(seller_name)
        reputation.add_success(order['buyer'])
        
        return jsonify({'success': True, 'amount_veil': order['amount_veil']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/confirm', methods=['POST'])
def p2p_confirm_receipt():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        wallet_name = d.get('wallet')
        confirm_type = d.get('confirm_type')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        
        if order['status'] != 'paid':
            return jsonify({'success': False, 'error': 'Status invalide'})
        
        if confirm_type == 'seller':
            order['seller_confirmed'] = True
        elif confirm_type == 'buyer':
            order['buyer_confirmed'] = True
        
        if order['seller_confirmed'] and order['buyer_confirmed']:
            order['status'] = 'completed'
            order['completed_at'] = time.time()
            buyer_wallet = active_wallets.get(order['buyer'])
            if buyer_wallet:
                buyer_wallet.balance += order['amount_veil']
                buyer_wallet.save()
        
        save_p2p_orders()
        
        if order['status'] == 'completed':
            return jsonify({'success': True, 'status': 'completed',
                           'message': f'Transaction complétée ! {order["amount_veil"]:.4f} VEIL transférés'})
        
        return jsonify({'success': True, 'status': 'waiting', 'message': 'En attente de l\'autre confirmation'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/cancel', methods=['POST'])
def p2p_cancel_order():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        wallet = d.get('wallet')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        if order['seller'] != wallet:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        if order['status'] != 'open':
            return jsonify({'success': False, 'error': 'Impossible d\'annuler'})
        
        seller_wallet = active_wallets.get(wallet)
        if seller_wallet:
            seller_wallet.balance += order['amount_veil']
            seller_wallet.save()
        
        del p2p_orders[order_id]
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Offre annulée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTE RÉPUTATION ====================

@web_bp.route('/api/p2p/reputation/<wallet>', methods=['GET'])
def get_reputation(wallet):
    try:
        status = reputation.get_status(wallet)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e), 'score': 100, 'status': '🟢 Actif', 'completed_trades': 0, 'failed_trades': 0, 'reports': 0})

# ==================== PREUVE DE PAIEMENT ====================

PROOF_DIR = os.path.join(DATA_DIR, "payment_proofs")
os.makedirs(PROOF_DIR, exist_ok=True)

@web_bp.route('/api/p2p/upload_proof', methods=['POST'])
def upload_payment_proof():
    try:
        order_id = request.form.get('order_id')
        buyer_name = request.form.get('buyer')
        file = request.files.get('proof')
        admin_seed = os.environ.get('ADMIN_SEED', '')
        
        if not file:
            return jsonify({'success': False, 'error': 'Aucun fichier'})
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        if order['buyer'] != buyer_name:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        image_data = base64.b64encode(file.read()).decode('utf-8')
        filename = secure_storage.store_payment_proof(order_id, buyer_name, image_data, admin_seed)
        
        order['payment_proof'] = filename
        order['proof_uploaded'] = True
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Preuve envoyée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/view_proof/<filename>', methods=['GET'])
def admin_view_proof(filename):
    try:
        admin_seed = request.args.get('admin_seed', '')
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 403
        
        proof = secure_storage.get_payment_proof(filename, admin_seed)
        if not proof:
            return jsonify({'error': 'Preuve non trouvée'}), 404
        
        return jsonify({'success': True, 'proof': proof})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN FORCE TRANSFER ====================

@web_bp.route('/api/admin/force_transfer', methods=['POST'])
def admin_force_transfer():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        from_wallet = d.get('from_wallet')
        to_wallet = d.get('to_wallet')
        amount = float(d.get('amount', 0))
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        
        if admin_seed != ADMIN_SEED:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        from_w = active_wallets.get(from_wallet)
        if not from_w:
            from_w = VeilWallet(from_wallet)
            from_w.load_or_create()
            active_wallets[from_wallet] = from_w
        
        to_w = active_wallets.get(to_wallet)
        if not to_w:
            to_w = VeilWallet(to_wallet)
            to_w.load_or_create()
            active_wallets[to_wallet] = to_w
        
        if from_w.balance < amount:
            return jsonify({'success': False, 'error': f'Solde insuffisant: {from_w.balance}'})
        
        from_w.balance -= amount
        to_w.balance += amount
        from_w.save()
        to_w.save()
        
        reputation.add_failure(from_wallet)
        
        return jsonify({'success': True, 'message': f'{amount} VEIL transférés'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== API STATS ====================

@web_bp.route('/api/stats')
def api_stats():
    return jsonify(get_blockchain_stats())

@web_bp.route('/api/blockchain/blocks')
def api_blocks():
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        return jsonify({'blocks': blocks[-20:], 'total': len(blocks)})
    return jsonify({'blocks': [], 'total': 0})

@web_bp.route('/ping')
def ping():
    return 'pong', 200

@web_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'wallets_count': len(active_wallets), 'mempool_size': len(mempool)})

# ==================== ADMIN BURN ====================

@web_bp.route('/api/admin/burn', methods=['POST'])
def admin_burn():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        amount_to_burn = float(d.get('amount', 0))
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        
        if admin_seed != ADMIN_SEED:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        if amount_to_burn <= 0:
            return jsonify({'success': False, 'error': 'Montant invalide'})
        
        global total_burned
        remaining_supply = MAX_SUPPLY - total_burned
        
        if amount_to_burn > remaining_supply:
            return jsonify({'success': False, 'error': f'Montant trop élevé. Supply restant: {remaining_supply} VEIL'})
        
        total_burned += amount_to_burn
        save_burn_stats()
        
        return jsonify({
            'success': True,
            'burned': amount_to_burn,
            'total_burned_since_start': total_burned,
            'remaining_supply': MAX_SUPPLY - total_burned,
            'burn_percentage': round((total_burned / MAX_SUPPLY) * 100, 4)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/burn/stats', methods=['GET'])
def admin_burn_stats():
    return jsonify({
        'total_burned': total_burned,
        'max_supply': MAX_SUPPLY,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': round((total_burned / MAX_SUPPLY) * 100, 4),
        'total_fees_collected': total_fees_collected
    })

@web_bp.route('/api/admin/burn/history', methods=['GET'])
def admin_burn_history():
    admin_seed = request.args.get('admin_seed', '')
    ADMIN_SEED = os.environ.get('ADMIN_SEED', 'ta_seed_admin_ici')
    
    if admin_seed != ADMIN_SEED:
        return jsonify({'error': 'Non autorisé'}), 403
    
    BURN_HISTORY_FILE = os.path.join(DATA_DIR, "burn_history.json")
    if os.path.exists(BURN_HISTORY_FILE):
        with open(BURN_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        return jsonify({'history': history, 'total': len(history)})
    return jsonify({'history': [], 'total': 0})

@web_bp.route('/burn/stats')
def burn_stats_page():
    return render_template('burn_stats.html')


@web_bp.route('/admin/login')
def admin_login_page():
    return render_template('admin_login.html')

@web_bp.route('/admin/proofs')
def admin_proofs_page():
    return render_template('admin_proofs.html')

@web_bp.route('/api/admin/pending_proofs', methods=['GET'])
def admin_pending_proofs():
    try:
        admin_seed = request.args.get('admin_seed', '')
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 403
        
        pending_orders = [o for o in p2p_orders.values() if o.get('payment_proof') and o.get('status') == 'paid']
        return jsonify({'orders': pending_orders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_bp.route('/api/admin/validate_proof', methods=['POST'])
def admin_validate_proof():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        order_id = d.get('order_id')
        action = d.get('action')
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        
        if admin_seed != ADMIN_SEED:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        
        if action == 'accept':
            buyer_wallet = active_wallets.get(order['buyer'])
            if not buyer_wallet:
                buyer_wallet = VeilWallet(order['buyer'])
                buyer_wallet.load_or_create()
                active_wallets[order['buyer']] = buyer_wallet
            
            seller_wallet = active_wallets.get(order['seller'])
            if not seller_wallet:
                seller_wallet = VeilWallet(order['seller'])
                seller_wallet.load_or_create()
                active_wallets[order['seller']] = seller_wallet
            
            buyer_wallet.balance += order['amount_veil']
            buyer_wallet.save()
            seller_wallet.save()
            
            order['status'] = 'completed'
            order['admin_validated'] = True
            save_p2p_orders()
            
            return jsonify({'success': True, 'message': '✅ Transaction validée'})
        
        elif action == 'reject':
            order['payment_proof'] = None
            order['proof_uploaded'] = False
            save_p2p_orders()
            return jsonify({'success': True, 'message': '❌ Preuve rejetée'})
        
        return jsonify({'success': False, 'error': 'Action inconnue'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
