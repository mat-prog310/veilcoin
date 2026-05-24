from flask import jsonify, request, render_template, session
from web.app import app
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.blockchain import Blockchain
from core.wallet import VeilWallet
from core.randomx_miner import RandomXMiner
from core.market import VeilMarket
from core.payment import LiquidityPool

blockchain = Blockchain()
market = VeilMarket(blockchain)
pool = LiquidityPool(market, blockchain)
market.current_price = pool.get_veil_price()
miner = None
active_wallets = {}

@app.route('/')
def index(): 
    return render_template('index.html', stats=blockchain.get_stats())

@app.route('/wallet')
def wallet_page(): 
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@app.route('/miner')
def miner_page():
    return render_template('miner.html', wallets=list(active_wallets.keys()))

@app.route('/blockchain')
def blockchain_page():
    return render_template('blockchain.html', stats=blockchain.get_stats())

@app.route('/market')
def market_page(): 
    return render_template('market.html', wallets=list(active_wallets.keys()))

# ==================== API ====================

@app.route('/api/stats')
def api_stats(): 
    return jsonify(blockchain.get_stats())

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    d = request.get_json()
    name = d.get('name', 'default').strip()
    w = VeilWallet(name)
    r = w.create_new()
    active_wallets[name] = w
    session['wallet_name'] = name
    return jsonify({'success': True, 'name': name, 'address': r['address'], 'seed_phrase': r['seed_phrase']})

@app.route('/api/wallet/login', methods=['POST'])
def api_login():
    d = request.get_json()
    name = d.get('name', '').strip()
    seed = d.get('seed_phrase', '').strip()
    w = VeilWallet(name)
    if not w.load_or_create(): return jsonify({'success': False, 'error': 'Wallet non trouvé'})
    if not w.verify_seed(seed): return jsonify({'success': False, 'error': 'Seed incorrecte'})
    active_wallets[name] = w
    session['wallet_name'] = name
    return jsonify({'success': True, 'name': name, 'address': w.address, 'balance': w.balance})

@app.route('/api/wallet/<name>/balance')
def api_balance(name):
    if name not in active_wallets: return jsonify({'balance_veil': 0})
    w = active_wallets[name]
    return jsonify({'name': name, 'balance_veil': w.balance})

# ==================== MINER ====================

@app.route('/api/miner/start', methods=['POST'])
def api_start_miner():
    global miner
    d = request.get_json(silent=True) or {}
    name = d.get('wallet', '')
    
    # Vérifier si wallet connecté
    if name not in active_wallets:
        return jsonify({'success': False, 'error': f'Wallet {name} non connecté. Créez/connectez votre wallet d\'abord.'})
    
    try:
        wallet = active_wallets[name]
        miner = RandomXMiner(blockchain)
        
        def cb(block):
            r = blockchain.reward()
            wallet.balance += r
            wallet.save()
        
        miner.set_callback(cb)
        miner.start_mining(wallet.address)
        return jsonify({'success': True, 'message': 'Minage démarré'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/miner/stop')
def api_stop_miner():
    global miner
    if miner:
        miner.stop_mining()
    return jsonify({'success': True})

@app.route('/api/miner/stats')
def api_miner_stats():
    if miner:
        return jsonify(miner.get_stats())
    return jsonify({'hashrate': 0, 'blocks_mined': 0})

# ==================== MARCHÉ ====================

@app.route('/api/market/price')
def api_price():
    return jsonify({'current_price': pool.get_veil_price()})

@app.route('/api/pool/info')
def api_pool_info():
    return jsonify(pool.get_pool_info())
