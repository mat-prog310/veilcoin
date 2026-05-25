from flask import jsonify, request, render_template, session
from web.app import app
import sys, os
import hashlib
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.blockchain import Blockchain
from core.wallet import VeilWallet
from core.randomx_miner import RandomXMiner
from core.market import VeilMarket
from core.payment import LiquidityPool
from config import Config

blockchain = Blockchain()
market = VeilMarket(blockchain)
pool = LiquidityPool(market, blockchain)
market.current_price = pool.get_veil_price()
miner = None
active_wallets = {}

import os

# Lire la seed depuis les variables d'environnement
ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
# Fichier pour stocker les blocs minés
MINED_BLOCKS_FILE = os.path.join(Config.DATA_DIR, "mined_blocks.json")
os.makedirs(Config.DATA_DIR, exist_ok=True)

@app.route('/')
def index(): 
    return render_template('index.html', stats=blockchain.get_stats())

@app.route('/wallet')
def wallet_page(): 
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@app.route('/blockchain')
def blockchain_page():
    from core.blockchain import Blockchain
    blockchain = Blockchain()
    blocks = blockchain.get_recent_blocks(20)
    stats = blockchain.get_stats()
    return render_template('blockchain.html', blocks=blocks, stats=stats)
    
@app.route('/market')
def market_page(): 
    return render_template('market.html', wallets=list(active_wallets.keys()))

# ==================== API WALLET ====================

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip() or 'default'
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        return jsonify({'success': True, 'name': name, 'address': r['address'], 'seed_phrase': r['seed_phrase'], 'balance': r['balance']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/login', methods=['POST'])
def api_login():
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

@app.route('/api/wallet/<name>/balance')
def api_balance(name):
    if name not in active_wallets:
        # Essayer de charger depuis le disque
        w = VeilWallet(name)
        if w.load_or_create():
            active_wallets[name] = w
            return jsonify({'name': name, 'balance_veil': w.balance, 'balance_eur': round(w.balance * pool.get_veil_price(), 6), 'veil_price': pool.get_veil_price()})
        return jsonify({'balance_veil': 0})
    w = active_wallets[name]
    return jsonify({'name': name, 'balance_veil': w.balance, 'balance_eur': round(w.balance * pool.get_veil_price(), 6), 'veil_price': pool.get_veil_price()})

@app.route('/api/wallet/<name>/send', methods=['POST'])
def api_send(name):
    try:
        d = request.get_json()
        to = d.get('to')
        amount = float(d.get('amount', 0))
        
        if name not in active_wallets:
            w = VeilWallet(name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[name] = w
        
        w = active_wallets[name]
        
        if w.balance < amount:
            return jsonify({'success': False, 'error': 'Solde insuffisant'})
        
        w.balance -= amount
        w.save()
        
        return jsonify({
            'success': True,
            'new_balance': w.balance,
            'to': to,
            'amount': amount
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

# ==================== API MINER (Difficulté 5 - EXTREME) ====================

@app.route('/api/miner/submit_block', methods=['POST'])
def submit_block():
    """Soumission d'un bloc par un mineur - Difficulté 5 (5 zéros)"""
    try:
        data = request.get_json()
        wallet = data.get('wallet')
        nonce = data.get('nonce')
        hash_proof = data.get('hash')
        base = data.get('base')
        submitted_diff = data.get('difficulty', 5)
        
        # VÉRIFICATION DIFFICULTÉ 5 (EXTREME)
        REQUIRED_DIFFICULTY = 5
        expected_prefix = "0" * REQUIRED_DIFFICULTY
        
        if not hash_proof.startswith(expected_prefix):
            return jsonify({
                'success': False, 
                'error': f'Preuve invalide - besoin de {REQUIRED_DIFFICULTY} zéros (hash: {hash_proof[:10]}...)'
            })
        
        # Récompenser le mineur
        w = VeilWallet(wallet)
        w.load_or_create()
        w.balance += 25
        w.save()
        active_wallets[wallet] = w
        
        # Sauvegarder le bloc trouvé
        block_record = {
            'index': len(blockchain.chain) + 1,
            'timestamp': time.time(),
            'miner': wallet,
            'hash': hash_proof,
            'nonce': nonce,
            'base': base,
            'reward': 25,
            'difficulty': REQUIRED_DIFFICULTY
        }
        
        # Sauvegarder dans un fichier
        existing_blocks = []
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
        
        existing_blocks.append(block_record)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks, f, indent=2)
        
        return jsonify({
            'success': True,
            'reward': 25,
            'new_balance': w.balance,
            'block_height': block_record['index'],
            'message': f'Bloc accepté ! +25 VEIL (difficulté {REQUIRED_DIFFICULTY})'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    """Statistiques de minage"""
    return jsonify({
        'difficulty': 5,
        'reward': 25,
        'required_zeros': 5,
        'estimated_hashes': 16**5,  # 1,048,576
        'network_hashrate': 0
    })

# ==================== API STATS ====================

@app.route('/api/stats')
def api_stats(): 
    return jsonify(blockchain.get_stats())

@app.route('/api/blockchain/blocks')
def api_blocks():
    """Retourne les blocs minés"""
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        return jsonify({'blocks': blocks[-20:], 'total': len(blocks)})
    return jsonify({'blocks': [], 'total': 0})

# ==================== API MARCHÉ ====================

@app.route('/api/market/price')
def api_price():
    return jsonify({'current_price': pool.get_veil_price(), 'pool_veil': pool.pool_veil, 'pool_eur': pool.pool_eur})

@app.route('/api/market/offers')
def api_offers(): 
    return jsonify(pool.get_open_sell_offers())

@app.route('/api/pool/info')
def api_pool_info(): 
    return jsonify(pool.get_pool_info())

# ==================== API TRÉSORERIE ====================

@app.route('/api/treasury')
def api_treasury():
    bill = pool.pay_server_bill()
    return jsonify({
        'treasury_veil': pool.treasury_veil,
        'treasury_eur': round(pool.treasury_eur, 2),
        'server_cost_monthly': pool.server_cost_eur,
        'can_pay_server': bill['can_pay'],
        'months_covered': bill.get('months_covered', 0)
    })

@app.route('/api/admin/reset', methods=['POST'])
def api_admin_reset():
    d = request.get_json()
    if d.get('seed') != ADMIN_SEED:
        return jsonify({'error': 'Non autorisé'}), 403
    if d.get('confirm') != 'yes':
        return jsonify({'error': 'Tape confirm=yes pour confirmer'}), 400
    
    import shutil
    data_dir = Config.DATA_DIR
    
    files = ['blockchain.json', 'mempool.json', 'market.json', 'pool.json', 'payments.json', 'peers.json']
    for f in files:
        path = os.path.join(data_dir, f)
        if os.path.exists(path):
            os.remove(path)
    
    wallets_dir = os.path.join(data_dir, 'wallets')
    if os.path.exists(wallets_dir):
        shutil.rmtree(wallets_dir)
    
    return jsonify({'success': True, 'message': 'Cache vidé. Redémarrage nécessaire.'})

@app.route('/ping')
def ping():
    return 'pong', 200
