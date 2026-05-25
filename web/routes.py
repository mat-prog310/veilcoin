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

ADMIN_SEED = "remplace_par_ta_seed_admin"

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

# ==================== API WALLET ====================

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip() or 'default'
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        return jsonify({'success': True, 'name': name, 'address': r['address'], 'seed_phrase': r['seed_phrase']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/login', methods=['POST'])
def api_login():
    d = request.get_json()
    name = d.get('name', '').strip()
    seed = d.get('seed_phrase', '').strip()
    w = VeilWallet(name)
    if not w.load_or_create(): return jsonify({'success': False, 'error': 'Wallet non trouvé'})
    if not w.verify_seed(seed): return jsonify({'success': False, 'error': 'Seed incorrecte'})
    active_wallets[name] = w
    return jsonify({'success': True, 'name': name, 'address': w.address, 'balance': w.balance})

@app.route('/api/wallet/<name>/balance')
def api_balance(name):
    if name not in active_wallets: return jsonify({'balance_veil': 0})
    w = active_wallets[name]
    return jsonify({'name': name, 'balance_veil': w.balance, 'balance_eur': round(w.balance * pool.get_veil_price(), 6), 'veil_price': pool.get_veil_price()})

@app.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

# ==================== API MINER ====================


# ==================== API STATS ====================

@app.route('/api/stats')
def api_stats(): 
    return jsonify(blockchain.get_stats())

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
