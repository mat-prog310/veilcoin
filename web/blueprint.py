# web/blueprint.py
from flask import Blueprint, jsonify, request, render_template
import sys, os
import hashlib
import time
import json

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
if pool:
    market.current_price = pool.get_veil_price()

active_wallets = {}
mempool = []

# Statistiques du burn
MAX_SUPPLY = 1_000_000_000
total_burned = 0
total_fees_collected = 0

# Fichiers de données
MINED_BLOCKS_FILE = os.path.join(Config.DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(Config.DATA_DIR, "burn_stats.json")
os.makedirs(Config.DATA_DIR, exist_ok=True)

# Stockage P2P
p2p_orders = {}
order_counter = 0

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
    if pool:
        pool.treasury_veil = getattr(pool, 'treasury_veil', 0) + treasury_amount
    return {
        'fee': fee,
        'burned': burn_amount,
        'treasury': treasury_amount,
        'total_burned_since_start': total_burned,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100
    }

# ==================== ROUTES ====================

@web_bp.route('/')
def index():
    stats = blockchain.get_stats() if blockchain else {'height': 0, 'difficulty': 5, 'total_supply': 0}
    stats['total_burned'] = total_burned
    stats['burn_percentage'] = (total_burned / MAX_SUPPLY) * 100
    stats['remaining_supply'] = MAX_SUPPLY - total_burned
    return render_template('index.html', stats=stats)

@web_bp.route('/wallet')
def wallet_page():
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@web_bp.route('/blockchain')
def blockchain_page():
    blocks = []
    stats = {'height': 0, 'difficulty': 5}
    if blockchain:
        blocks = blockchain.get_recent_blocks(20)
        stats = blockchain.get_stats()
    stats['total_burned'] = total_burned
    stats['burn_percentage'] = (total_burned / MAX_SUPPLY) * 100
    return render_template('blockchain.html', blocks=blocks[-20:], stats=stats)

@web_bp.route('/market')
def market_page():
    return render_template('market.html', wallets=list(active_wallets.keys()))

# ==================== API ROUTES ====================

@web_bp.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip() or 'default'
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        return jsonify({'success': True, 'name': name, 'address': r['address'], 'seed_phrase': r['seed_phrase'], 'balance': r.get('balance', 0)})
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
        price = pool.get_veil_price() if pool else 0.042
        return jsonify({'name': name, 'balance_veil': w.balance, 'balance_eur': round(w.balance * price, 6), 'veil_price': price})
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
        transaction = {'from': w.address, 'to': to, 'amount': amount, 'fee': fee, 'timestamp': time.time()}
        mempool.append(transaction)
        return jsonify({'success': True, 'new_balance': w.balance, 'fee': fee, 'burned': burn_result['burned']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/submit_block', methods=['POST'])
def submit_block():
    try:
        data = request.get_json()
        wallet = data.get('wallet')
        nonce = data.get('nonce')
        hash_proof = data.get('hash')
        previous_hash = data.get('previous_hash', '')
        transactions = data.get('transactions', [])
        if not hash_proof.startswith('0' * 5):
            return jsonify({'success': False, 'error': 'Preuve invalide'})
        last_block_hash = "0" * 64
        last_block_index = 0
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
                if existing_blocks:
                    last_block = existing_blocks[-1]
                    last_block_hash = last_block.get('hash', "0" * 64)
                    last_block_index = last_block.get('index', 0)
        new_block = {
            'index': last_block_index + 1,
            'timestamp': time.time(),
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': previous_hash or last_block_hash,
            'hash': hash_proof,
            'miner': wallet,
            'reward_miner': 25,
            'reward_pool': 25,
            'difficulty': 5
        }
        existing_blocks = []
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
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
        return jsonify({'success': True, 'reward_miner': 25, 'new_balance': w.balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

@web_bp.route('/api/stats')
def api_stats():
    return jsonify({'height': 0, 'difficulty': 5, 'mempool_size': len(mempool), 'total_burned': total_burned})

@web_bp.route('/ping')
def ping():
    return 'pong', 200

@web_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'mempool_size': len(mempool), 'total_burned': total_burned})
