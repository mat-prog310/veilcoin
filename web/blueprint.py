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

# Initialisation
try:
    from core.blockchain import Blockchain
    blockchain = Blockchain()
except:
    blockchain = None
    print("⚠️ Blockchain non disponible")

market = VeilMarket(blockchain) if blockchain else None
pool = LiquidityPool(market, blockchain) if market else None

# FORCER LA POOL À 0.01 EUR
if pool:
    pool.pool_veil = 1000000
    pool.pool_eur = 10000
    print(f"✅ Pool: {pool.pool_veil} VEIL / {pool.pool_eur} EUR")
    print(f"💰 Prix: {pool.get_veil_price():.4f} EUR/VEIL")
else:
    # Créer une pool manuellement
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

# ==================== STATS BURN ====================
MAX_SUPPLY = 1_000_000_000
total_burned = 0
total_fees_collected = 0

DATA_DIR = Config.DATA_DIR
MINED_BLOCKS_FILE = os.path.join(DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(DATA_DIR, "burn_stats.json")
os.makedirs(DATA_DIR, exist_ok=True)

# Créer un bloc genesis si nécessaire
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

# Charger les stats de burn
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
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

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
                         pool_eur=pool.pool_eur if pool else 0)

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
        mempool.append({'from': w.address, 'to': to, 'amount': amount, 'fee': fee})
        return jsonify({'success': True, 'new_balance': w.balance, 'fee': fee, 'burned': burn_result['burned']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

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
        
        return jsonify({'success': True, 'reward_miner': 25, 'new_balance': w.balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    return jsonify({'difficulty': 5, 'reward': 25, 'required_zeros': 5})

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
        'max_supply': MAX_SUPPLY,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
    })

# ==================== PING ====================

@web_bp.route('/ping')
def ping():
    return 'pong', 200

@web_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'pool': pool is not None, 'mempool_size': len(mempool)})
