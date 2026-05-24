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
def index(): return render_template('index.html', stats=blockchain.get_stats())

@app.route('/wallet')
def wallet_page(): return render_template('wallet.html', wallets=list(active_wallets.keys()))

@app.route('/miner')
def miner_page():
    return render_template('miner.html', wallets=list(active_wallets.keys()),
                          miner_stats=miner.get_stats() if miner else None,
                          is_mining=miner.is_mining if miner else False)

@app.route('/blockchain')
def blockchain_page():
    return render_template('blockchain.html', stats=blockchain.get_stats(),
                          blocks=blockchain.get_recent_blocks(20))

@app.route('/market')
def market_page(): return render_template('market.html', wallets=list(active_wallets.keys()))

# ==================== API ====================

@app.route('/api/stats')
def api_stats(): return jsonify(blockchain.get_stats())

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    d = request.get_json()
    name = d.get('name', 'default').strip()
    if name in active_wallets: return jsonify({'error': 'Wallet déjà chargé'}), 400
    w = VeilWallet(name)
    r = w.create_new()
    active_wallets[name] = w
    return jsonify({'success': True, 'name': name, 'address': r['address'], 'seed_phrase': r['seed_phrase']})

@app.route('/api/wallet/login', methods=['POST'])
def api_login():
    d = request.get_json()
    name = d.get('name', '').strip()
    seed = d.get('seed_phrase', '').strip()
    w = VeilWallet(name)
    if not w.load_or_create(): return jsonify({'error': 'Wallet non trouvé'}), 404
    if not w.verify_seed(seed): return jsonify({'error': 'Seed incorrecte'}), 403
    active_wallets[name] = w
    session['wallet_name'] = name
    return jsonify({'success': True, 'name': name, 'address': w.address, 'balance': w.balance})

@app.route('/api/wallet/<name>/balance')
def api_balance(name):
    if name not in active_wallets: return jsonify({'error': 'Non connecté'}), 404
    w = active_wallets[name]
    w.balance = blockchain.get_balance(w.address)
    w.save()
    return jsonify({'name': name, 'address': w.address, 'balance_veil': w.balance,
                    'balance_eur': round(w.balance * pool.get_veil_price(), 6),
                    'veil_price': pool.get_veil_price()})

@app.route('/api/wallet/<name>/transactions')
def api_tx(name):
    if name not in active_wallets: return jsonify([])
    return jsonify(active_wallets[name].get_recent_transactions(20))

@app.route('/api/wallet/logout', methods=['POST'])
def api_logout(): session.pop('wallet_name', None); return jsonify({'success': True})

# ==================== MINER ====================

@app.route('/api/miner/start', methods=['POST'])
def api_start_miner():
    global miner
    d = request.get_json()
    name = d.get('wallet')
    
    if name not in active_wallets:
        return jsonify({'success': False, 'error': 'Wallet non connecté'}), 404
    
    wallet = active_wallets[name]
    miner = RandomXMiner(blockchain)
    miner.set_callback(lambda block: None)
    miner.start_mining(wallet.address)
    
    return jsonify({'success': True})

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
    return jsonify({'hashrate': 0, 'blocks_mined': 0, 'accepted_shares': 0, 'current_difficulty': 2})

# ==================== MARCHÉ ====================

@app.route('/api/market/price')
def api_price():
    return jsonify({'current_price': pool.get_veil_price(), 'reference_price': pool.get_reference_price()})

@app.route('/api/market/create-offer', methods=['POST'])
def api_create_offer():
    d = request.get_json()
    return jsonify(pool.create_sell_offer(d.get('wallet'), float(d.get('amount', 0)),
           float(d.get('price_per_veil', 0.0001)), d.get('paypal_email', '')))

@app.route('/api/market/create-buy-offer', methods=['POST'])
def api_create_buy_offer():
    d = request.get_json()
    return jsonify(pool.create_buy_offer(d.get('wallet'), float(d.get('amount', 0)),
           float(d.get('price_per_veil', 0.0001)), d.get('paypal_email', '')))

@app.route('/api/market/buyer-lock', methods=['POST'])
def api_buyer_lock():
    d = request.get_json()
    return jsonify(pool.buyer_lock_funds(d.get('offer_id'), d.get('wallet'), d.get('buyer_paypal', '')))

@app.route('/api/market/seller-accept', methods=['POST'])
def api_seller_accept():
    d = request.get_json()
    return jsonify(pool.seller_accept_buyer(d.get('offer_id'), d.get('wallet')))

@app.route('/api/market/seller-lock', methods=['POST'])
def api_seller_lock():
    d = request.get_json()
    return jsonify(pool.seller_lock_veil(d.get('offer_id'), d.get('wallet')))

@app.route('/api/market/buyer-accept-seller', methods=['POST'])
def api_buyer_accept_seller():
    d = request.get_json()
    return jsonify(pool.buyer_accept_seller(d.get('offer_id'), d.get('wallet'), d.get('buyer_paypal', '')))

@app.route('/api/market/confirm', methods=['POST'])
def api_confirm():
    d = request.get_json()
    return jsonify(pool.confirm_payment(d.get('offer_id'), d.get('wallet')))

@app.route('/api/market/cancel', methods=['POST'])
def api_cancel():
    d = request.get_json()
    return jsonify(pool.cancel_offer(d.get('offer_id'), d.get('wallet')))

@app.route('/api/market/sell-offers')
def api_sell_offers(): return jsonify(pool.get_open_sell_offers())

@app.route('/api/market/buy-offers')
def api_buy_offers(): return jsonify(pool.get_open_buy_offers())

@app.route('/api/pool/info')
def api_pool_info(): return jsonify(pool.get_pool_info())
