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

# Création du Blueprint
web_bp = Blueprint('web', __name__, template_folder='../templates')

# ==================== ANTI-DUMP & ANTI-PUMP ====================
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
    print(f"✅ Pool: {pool.pool_veil} VEIL / {pool.pool_eur} EUR")
    print(f"💰 Prix: {pool.get_veil_price():.4f} EUR/VEIL")
else:
    class DummyPool:
        def __init__(self):
            self.pool_veil = 1000000
            self.pool_eur = 10000
            self.treasury_veil = 0
        def get_veil_price(self):
            return self.pool_eur / self.pool_veil if self.pool_veil > 0 else 0.01
    pool = DummyPool()
    print("✅ Pool créée manuellement")

active_wallets = {}
mempool = []

MAX_SUPPLY = 1_000_000_000
total_burned = 0
total_fees_collected = 0

DATA_DIR = Config.DATA_DIR
MINED_BLOCKS_FILE = os.path.join(DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(DATA_DIR, "burn_stats.json")
os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(MINED_BLOCKS_FILE):
    genesis_block = {
        'index': 0,
        'timestamp': time.time(),
        'transactions': [],
        'nonce': 0,
        'previous_hash': '0' * 64,
        'hash': hashlib.sha256(b'VEILCOIN_GENESIS').hexdigest(),
        'miner': 'system',
        'reward_miner': 0,
        'reward_pool': 0,
        'difficulty': 5
    }
    with open(MINED_BLOCKS_FILE, 'w') as f:
        json.dump([genesis_block], f, indent=2)
    print("✅ Bloc genesis créé")

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
        'fee': fee,
        'burned': burn_amount,
        'treasury': treasury_amount,
        'total_burned_since_start': total_burned,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
    }

def check_anti_manipulation(wallet, amount_veil, is_buy):
    global user_last_trade, user_trade_count
    now = time.time()
    if wallet in user_last_trade:
        elapsed = now - user_last_trade[wallet]
        if elapsed < MIN_TRADE_INTERVAL:
            return False, f"Attendez {MIN_TRADE_INTERVAL - elapsed:.0f} secondes"
    max_trade = pool.pool_veil * (MAX_TRADE_PERCENT / 100)
    if amount_veil > max_trade:
        return False, f"Maximum {MAX_TRADE_PERCENT}% de la pool ({max_trade:.0f} VEIL)"
    if wallet in user_trade_count:
        if user_trade_count[wallet] >= COOLDOWN_BLOCKS:
            return False, f"Trop de trades. Attendez {COOLDOWN_BLOCKS} blocs"
    return True, "OK"

def update_trade_record(wallet):
    global user_last_trade, user_trade_count
    user_last_trade[wallet] = time.time()
    user_trade_count[wallet] = user_trade_count.get(wallet, 0) + 1

def get_blockchain_stats():
    stats = {
        'height': 0,
        'difficulty': 5,
        'total_supply': 0,
        'total_burned': total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'mempool_size': len(mempool)
    }
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                blocks = json.load(f)
                stats['height'] = len(blocks)
        except:
            pass
    return stats

def get_recent_blocks(n=20):
    blocks = []
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                all_blocks = json.load(f)
                for b in all_blocks[-n:]:
                    blocks.append({
                        'index': b.get('index', 0),
                        'hash': b.get('hash', '')[:20],
                        'full_hash': b.get('hash', ''),
                        'tx_count': len(b.get('transactions', [])),
                        'nonce': b.get('nonce', 0),
                        'difficulty': b.get('difficulty', 5),
                        'timestamp': b.get('timestamp', time.time()),
                        'miner': b.get('miner', 'unknown')[:15]
                    })
        except:
            pass
    return blocks

@web_bp.app_template_filter('datetime')
def format_datetime(timestamp):
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")

# ==================== PAGES WEB ====================

@web_bp.route('/')
def index():
    stats = get_blockchain_stats()
    return render_template('index.html', stats=stats)

@web_bp.route('/wallet')
def wallet_page():
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@web_bp.route('/blockchain')
def blockchain_page():
    blocks = get_recent_blocks(20)
    stats = get_blockchain_stats()
    return render_template('blockchain.html', blocks=blocks, stats=stats)

@web_bp.route('/market')
def market_page():
    price = pool.get_veil_price() if pool else 0.01
    return render_template('market.html', 
                         price=round(price, 4),
                         pool_veil=pool.pool_veil if pool else 0,
                         pool_eur=pool.pool_eur if pool else 0,
                         max_trade_percent=MAX_TRADE_PERCENT,
                         cooldown_seconds=MIN_TRADE_INTERVAL)

# ==================== API WALLET ====================

@web_bp.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip() or 'default'
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        return jsonify({
            'success': True, 
            'name': name, 
            'address': r['address'], 
            'seed_phrase': r['seed_phrase'],
            'balance': r.get('balance', 0)
        })
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
        return jsonify({
            'success': True, 
            'name': name, 
            'address': w.address, 
            'balance': w.balance
        })
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
        return jsonify({
            'name': name, 
            'balance_veil': w.balance, 
            'balance_eur': round(w.balance * price, 6), 
            'veil_price': price
        })
    except:
        return jsonify({'balance_veil': 0})

@web_bp.route('/api/wallet/<name>/send', methods=['POST'])
def api_send(name):
    try:
        d = request.get_json()
        to = d.get('to')
        amount = float(d.get('amount', 0))
        
        if name in active_wallets:
            w = active_wallets[name]
        else:
            w = VeilWallet(name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[name] = w
        
        fee = calculate_fee(amount)
        total = amount + fee
        
        if w.balance < total:
            return jsonify({'success': False, 'error': f'Solde insuffisant'})
        
        burn_result = apply_burn(fee)
        w.balance -= total
        w.save()
        
        mempool.append({
            'from': w.address, 
            'to': to, 
            'amount': amount, 
            'fee': fee,
            'burned': burn_result['burned']
        })
        
        return jsonify({
            'success': True, 
            'new_balance': w.balance, 
            'fee': fee, 
            'burned': burn_result['burned']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

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
        
        if not pool:
            return jsonify({'success': False, 'error': 'Pool non disponible'})
        
        current_price = pool.get_veil_price()
        veil_amount = eur_amount / current_price
        
        allowed, msg = check_anti_manipulation(wallet_name, veil_amount, True)
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
        
        return jsonify({
            'success': True,
            'veil_received': veil_amount,
            'eur_spent': eur_amount,
            'new_balance': w.balance,
            'new_price': new_price,
            'price_change': round(((new_price - current_price) / current_price) * 100, 2)
        })
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
        
        if not pool:
            return jsonify({'success': False, 'error': 'Pool non disponible'})
        
        if w.balance < veil_amount:
            return jsonify({'success': False, 'error': 'Solde insuffisant'})
        
        current_price = pool.get_veil_price()
        eur_amount = veil_amount * current_price
        
        allowed, msg = check_anti_manipulation(wallet_name, veil_amount, False)
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
        
        return jsonify({
            'success': True,
            'eur_received': eur_amount,
            'veil_sold': veil_amount,
            'new_balance': w.balance,
            'new_price': new_price,
            'price_change': round(((new_price - current_price) / current_price) * 100, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
            'reward_miner': 25,
            'reward_pool': 25,
            'difficulty': 5
        }
        
        existing_blocks.append(new_block)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks[-100:], f, indent=2)
        
        w = VeilWallet(wallet)
        w.load_or_create()
        w.balance += 25
        w.save()
        active_wallets[wallet] = w
        
        if pool:
            pool.pool_veil = getattr(pool, 'pool_veil', 0) + 25
        
        global user_trade_count
        for wallet_key in list(user_trade_count.keys()):
            user_trade_count[wallet_key] = max(0, user_trade_count[wallet_key] - 1)
        
        return jsonify({'success': True, 'reward_miner': 25, 'new_balance': w.balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    return jsonify({'difficulty': 5, 'reward': 25, 'required_zeros': 5, 'estimated_hashes': 1048576})

@web_bp.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

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

@web_bp.route('/api/market/price')
def api_price():
    price = pool.get_veil_price() if pool else 0.01
    return jsonify({'current_price': price, 'pool_veil': pool.pool_veil if pool else 0, 'pool_eur': pool.pool_eur if pool else 0})

@web_bp.route('/api/burn/stats')
def api_burn_stats():
    return jsonify({
        'total_burned': total_burned,
        'total_fees_collected': total_fees_collected,
        'max_supply': MAX_SUPPLY,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
    })

# ==================== PING & HEALTH ====================

@web_bp.route('/ping')
def ping():
    return 'pong', 200

@web_bp.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'pool': pool is not None,
        'wallets_count': len(active_wallets),
        'mempool_size': len(mempool),
        'total_burned': total_burned
    })
