# web/blueprint.py
from flask import Blueprint, jsonify, request, render_template
import sys, os
import hashlib
import time
import json
# Initialisation de la pool avec des liquidités par défaut
if pool and pool.pool_veil == 0 and pool.pool_eur == 0:
    pool.pool_veil = 100000  # 100k VEIL
    pool.pool_eur = 10000    # 10k EUR
    print(f"✅ Pool initialisée: {pool.pool_veil} VEIL / {pool.pool_eur} EUR = {pool.get_veil_price():.4f} EUR/VEIL")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wallet import VeilWallet
from core.market import VeilMarket
from core.payment import LiquidityPool
from config import Config

# Création du Blueprint
web_bp = Blueprint('web', __name__, template_folder='../templates')

# Initialisation (sans blockchain)
try:
    from core.blockchain import Blockchain
    blockchain = Blockchain()
except:
    blockchain = None
    print("⚠️ Blockchain non disponible - Utilisation du stockage JSON")

market = VeilMarket(blockchain) if blockchain else None
pool = LiquidityPool(market, blockchain) if market else None
if pool:
    market.current_price = pool.get_veil_price()

active_wallets = {}
mempool = []

# ==================== STATS BURN ====================
MAX_SUPPLY = 1_000_000_000
total_burned = 0
total_fees_collected = 0

# Fichiers de données
DATA_DIR = Config.DATA_DIR
MINED_BLOCKS_FILE = os.path.join(DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(DATA_DIR, "burn_stats.json")
os.makedirs(DATA_DIR, exist_ok=True)

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
    if pool:
        pool.treasury_veil = getattr(pool, 'treasury_veil', 0) + treasury_amount
    return {
        'fee': fee,
        'burned': burn_amount,
        'treasury': treasury_amount,
        'total_burned_since_start': total_burned,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
    }

def get_blockchain_stats():
    """Récupère les stats depuis mined_blocks.json"""
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
    """Récupère les n derniers blocs depuis mined_blocks.json"""
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
                        'miner': b.get('miner', 'unknown')
                    })
        except:
            pass
    return blocks

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
    blocks = []
    stats = {
        'height': 0,
        'difficulty': 5,
        'total_supply': 0,
        'total_burned': total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'mempool_size': len(mempool)
    }
    
    # Lire les blocs depuis mined_blocks.json
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                all_blocks = json.load(f)
                stats['height'] = len(all_blocks)
                
                # Prendre les 20 derniers blocs
                for b in all_blocks[-20:]:
                    blocks.append({
                        'index': b.get('index', 0),
                        'hash': b.get('hash', '')[:20] + '...',
                        'full_hash': b.get('hash', ''),
                        'tx_count': len(b.get('transactions', [])),
                        'nonce': b.get('nonce', 0),
                        'difficulty': b.get('difficulty', 5),
                        'timestamp': b.get('timestamp', time.time()),
                        'miner': b.get('miner', 'unknown')[:20] + '...' if len(b.get('miner', '')) > 20 else b.get('miner', 'unknown')
                    })
        except Exception as e:
            print(f"Erreur lecture blocs: {e}")
    
    # Créer un bloc genesis si aucun bloc n'existe
    if not blocks:
        genesis_block = {
            'index': 0,
            'hash': '00000...GENESIS...',
            'full_hash': '0000000000000000000000000000000000000000000000000000000000000000',
            'tx_count': 0,
            'nonce': 0,
            'difficulty': 5,
            'timestamp': time.time(),
            'miner': 'system'
        }
        blocks.append(genesis_block)
        stats['height'] = 1
    
    return render_template('blockchain.html', blocks=blocks, stats=stats)

@web_bp.route('/market')
def market_page():
    return render_template('market.html', wallets=list(active_wallets.keys()))

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
        
        price = pool.get_veil_price() if pool else 0.042
        return jsonify({
            'name': name, 
            'balance_veil': w.balance, 
            'balance_eur': round(w.balance * price, 6), 
            'veil_price': price,
            'total_burned': total_burned,
            'burn_percentage': (total_burned / MAX_SUPPLY) * 100 if MAX_SUPPLY > 0 else 0
        })
    except Exception as e:
        return jsonify({'balance_veil': 0, 'error': str(e)})

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
        total_amount = amount + fee
        
        if w.balance < total_amount:
            return jsonify({'success': False, 'error': f'Solde insuffisant. Nécessaire: {total_amount:.4f} VEIL'})
        
        burn_result = apply_burn(fee)
        
        w.balance -= total_amount
        w.save()
        
        transaction = {
            'from': w.address,
            'to': to,
            'amount': amount,
            'fee': fee,
            'burned': burn_result['burned'],
            'treasury': burn_result['treasury'],
            'timestamp': time.time(),
            'signature': hashlib.sha256(f"{w.address}{to}{amount}{fee}{time.time()}".encode()).hexdigest()
        }
        
        mempool.append(transaction)
        
        return jsonify({
            'success': True,
            'new_balance': w.balance,
            'to': to,
            'amount': amount,
            'fee': fee,
            'burned': burn_result['burned'],
            'burn_percentage': burn_result['burn_percentage'],
            'total_burned_since_start': burn_result['total_burned_since_start'],
            'message': f'Transaction envoyée ! Frais: {fee:.4f} VEIL (dont {burn_result["burned"]:.4f} brûlés)'
        })
        
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
        previous_hash = data.get('previous_hash', '')
        transactions = data.get('transactions', [])
        
        REQUIRED_DIFFICULTY = 5
        
        if not hash_proof.startswith('0' * REQUIRED_DIFFICULTY):
            return jsonify({'success': False, 'error': f'Preuve invalide - besoin de {REQUIRED_DIFFICULTY} zéros'})
        
        # Lire les blocs existants
        existing_blocks = []
        last_block_hash = "0" * 64
        last_block_index = 0
        
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
                if existing_blocks:
                    last_block = existing_blocks[-1]
                    last_block_hash = last_block.get('hash', "0" * 64)
                    last_block_index = last_block.get('index', 0)
        
        # Créer le nouveau bloc
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
            'total_reward': 50,
            'difficulty': REQUIRED_DIFFICULTY
        }
        
        # Sauvegarder
        existing_blocks.append(new_block)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks[-100:], f, indent=2)
        
        # Récompenser le mineur
        w = VeilWallet(wallet)
        w.load_or_create()
        w.balance += 25
        w.save()
        active_wallets[wallet] = w
        
        # Ajouter à la pool
        if pool:
            pool.pool_veil = getattr(pool, 'pool_veil', 0) + 25
        
        # Vider la mempool
        for tx in transactions:
            if tx in mempool:
                mempool.remove(tx)
        
        return jsonify({
            'success': True,
            'reward_miner': 25,
            'reward_pool': 25,
            'total_reward': 50,
            'new_balance': w.balance,
            'block_index': new_block['index'],
            'block_hash': hash_proof,
            'message': f'Bloc #{new_block["index"]} validé ! +25 VEIL pour vous'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    blocks_count = 0
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                blocks_count = len(json.load(f))
        except:
            pass
    
    return jsonify({
        'difficulty': 5,
        'reward': 25,
        'required_zeros': 5,
        'estimated_hashes': 1048576,
        'network_hashrate': 0,
        'mempool_size': len(mempool),
        'total_blocks': blocks_count
    })

@web_bp.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

# ==================== API STATS ====================

@web_bp.route('/api/stats')
def api_stats():
    stats = get_blockchain_stats()
    return jsonify(stats)

@web_bp.route('/api/blockchain/blocks')
def api_blocks():
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        return jsonify({'blocks': blocks[-20:], 'total': len(blocks)})
    return jsonify({'blocks': [], 'total': 0})

@web_bp.route('/api/market/price')
def api_price():
    if pool:
        return jsonify({
            'current_price': pool.get_veil_price(), 
            'pool_veil': getattr(pool, 'pool_veil', 0), 
            'pool_eur': getattr(pool, 'pool_eur', 0)
        })
    return jsonify({'current_price': 0.042, 'pool_veil': 0, 'pool_eur': 0})

@web_bp.route('/api/market/offers')
def api_offers():
    if pool:
        return jsonify(pool.get_open_sell_offers())
    return jsonify([])

@web_bp.route('/api/pool/info')
def api_pool_info():
    if pool:
        return jsonify(pool.get_pool_info())
    return jsonify({})

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
    blocks_count = 0
    if os.path.exists(MINED_BLOCKS_FILE):
        try:
            with open(MINED_BLOCKS_FILE, 'r') as f:
                blocks_count = len(json.load(f))
        except:
            pass
    
    return jsonify({
        'status': 'ok',
        'pool': pool is not None,
        'wallets_count': len(active_wallets),
        'mempool_size': len(mempool),
        'total_burned': total_burned,
        'total_blocks': blocks_count
    })
