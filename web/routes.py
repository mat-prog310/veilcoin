from flask import jsonify, request, render_template, session
from web.app import app
import sys, os
import hashlib
import time
import json
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.wallet import VeilWallet
from core.market import VeilMarket
from core.payment import LiquidityPool
from config import Config

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

miner = None
active_wallets = {}
mempool = []

# 📊 STATISTIQUES DU BURN (1 Milliard de tokens)
MAX_SUPPLY = 1_000_000_000  # 1 milliard
total_burned = 0
total_fees_collected = 0

# 🔐 SEED ADMIN
ADMIN_SEED = os.environ.get('ADMIN_SEED', '')

# Fichiers de données
MINED_BLOCKS_FILE = os.path.join(Config.DATA_DIR, "mined_blocks.json")
BURN_STATS_FILE = os.path.join(Config.DATA_DIR, "burn_stats.json")
os.makedirs(Config.DATA_DIR, exist_ok=True)

# Stockage des transactions P2P
p2p_orders = {}
order_counter = 0

# Charger les stats de burn
if os.path.exists(BURN_STATS_FILE):
    with open(BURN_STATS_FILE, 'r') as f:
        burn_data = json.load(f)
        total_burned = burn_data.get('total_burned', 0)
        total_fees_collected = burn_data.get('total_fees_collected', 0)

def save_burn_stats():
    """Sauvegarde les statistiques de burn"""
    with open(BURN_STATS_FILE, 'w') as f:
        json.dump({
            'total_burned': total_burned,
            'total_fees_collected': total_fees_collected,
            'max_supply': MAX_SUPPLY,
            'last_update': time.time()
        }, f, indent=2)

def calculate_fee(amount):
    """Calcule les frais (1% de la transaction)"""
    fee = amount * 0.01
    return round(fee, 8)

def apply_burn(fee):
    """Applique le burn sur les frais (50% brûlés, 50% trésorerie)"""
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

# ==================== PAGES WEB ====================

@app.route('/')
def index(): 
    stats = blockchain.get_stats() if blockchain else {'height': 0, 'difficulty': 5, 'total_supply': 0}
    stats['total_burned'] = total_burned
    stats['total_fees'] = total_fees_collected
    stats['remaining_supply'] = MAX_SUPPLY - total_burned
    stats['burn_percentage'] = (total_burned / MAX_SUPPLY) * 100
    return render_template('index.html', stats=stats)

@app.route('/wallet')
def wallet_page(): 
    return render_template('wallet.html', wallets=list(active_wallets.keys()))

@app.route('/blockchain')
def blockchain_page():
    blocks = []
    stats = {'height': 0, 'difficulty': 5}
    
    if blockchain:
        blocks = blockchain.get_recent_blocks(20)
        stats = blockchain.get_stats()
    
    stats['total_burned'] = total_burned
    stats['burn_percentage'] = (total_burned / MAX_SUPPLY) * 100
    
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            mined = json.load(f)
            for b in mined[-20:]:
                blocks.append({
                    'index': b.get('index', 0),
                    'hash': b.get('hash', '')[:20],
                    'full_hash': b.get('hash', ''),
                    'tx_count': len(b.get('transactions', [])),
                    'nonce': b.get('nonce', 0),
                    'difficulty': 5,
                    'timestamp': b.get('timestamp', time.time()),
                    'miner': b.get('miner', 'unknown')
                })
    
    return render_template('blockchain.html', blocks=blocks[-20:], stats=stats)

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
        return jsonify({
            'success': True, 
            'name': name, 
            'address': r['address'], 
            'seed_phrase': r['seed_phrase'],
            'balance': r.get('balance', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/login', methods=['POST'])
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

@app.route('/api/wallet/<name>/balance')
def api_balance(name):
    try:
        if name in active_wallets:
            w = active_wallets[name]
        else:
            w = VeilWallet(name)
            if not w.load_or_create():
                return jsonify({'balance_veil': 0, 'error': 'Wallet non trouvé'})
            active_wallets[name] = w
        
        price = pool.get_veil_price() if pool else 0.042
        return jsonify({
            'name': name, 
            'balance_veil': w.balance, 
            'balance_eur': round(w.balance * price, 6), 
            'veil_price': price,
            'total_burned': total_burned,
            'burn_percentage': (total_burned / MAX_SUPPLY) * 100
        })
    except Exception as e:
        return jsonify({'balance_veil': 0, 'error': str(e)})

@app.route('/api/wallet/<name>/send', methods=['POST'])
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
            return jsonify({'success': False, 'error': f'Solde insuffisant. Nécessaire: {total_amount:.4f} VEIL (dont {fee:.4f} VEIL de frais)'})
        
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
            'remaining_supply': burn_result['remaining_supply'],
            'message': f'Transaction envoyée ! Frais: {fee:.4f} VEIL (dont {burn_result["burned"]:.4f} brûlés)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

# ==================== API MINER ====================

@app.route('/api/miner/submit_block', methods=['POST'])
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
            'total_reward': 50,
            'difficulty': REQUIRED_DIFFICULTY
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
            'message': f'Bloc #{new_block["index"]} validé ! +25 VEIL pour vous, +25 VEIL pour la pool'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    return jsonify({
        'difficulty': 5,
        'reward': 25,
        'required_zeros': 5,
        'estimated_hashes': 1048576,
        'network_hashrate': 0,
        'mempool_size': len(mempool),
        'total_blocks': len(json.load(open(MINED_BLOCKS_FILE))) if os.path.exists(MINED_BLOCKS_FILE) else 0
    })

@app.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

# ==================== API P2P ESCROW ====================

@app.route('/api/p2p/create', methods=['POST'])
def p2p_create_order():
    global order_counter
    try:
        d = request.get_json()
        wallet_name = d.get('wallet')
        type_order = d.get('type')
        amount_veil = float(d.get('amount_veil', 0))
        price_eur = float(d.get('price_eur', 0))
        payment_method = d.get('payment_method', 'paypal')
        
        if wallet_name not in active_wallets:
            w = VeilWallet(wallet_name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[wallet_name] = w
        else:
            w = active_wallets[wallet_name]
        
        if type_order == 'sell' and w.balance < amount_veil:
            return jsonify({'success': False, 'error': f'Solde insuffisant: {w.balance:.4f} VEIL'})
        
        order_counter += 1
        order_id = f"P2P_{order_counter}_{int(time.time())}"
        
        p2p_orders[order_id] = {
            'id': order_id,
            'seller': wallet_name if type_order == 'sell' else None,
            'buyer': wallet_name if type_order == 'buy' else None,
            'type': type_order,
            'amount_veil': amount_veil,
            'price_eur': price_eur,
            'total_eur': amount_veil * price_eur,
            'payment_method': payment_method,
            'status': 'open',
            'seller_email': None,
            'buyer_email': None,
            'seller_confirmed': False,
            'buyer_confirmed': False,
            'created_at': time.time(),
            'escrow_veil': None,
            'transaction_id': None
        }
        
        if type_order == 'sell':
            w.balance -= amount_veil
            p2p_orders[order_id]['escrow_veil'] = amount_veil
            w.save()
        
        return jsonify({'success': True, 'order_id': order_id, 'order': p2p_orders[order_id]})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/p2p/match', methods=['POST'])
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
        
        if order['type'] != 'sell':
            return jsonify({'success': False, 'error': 'Seule une offre de vente peut être acceptée'})
        
        if buyer_name not in active_wallets:
            w = VeilWallet(buyer_name)
            if not w.load_or_create():
                return jsonify({'success': False, 'error': 'Wallet non trouvé'})
            active_wallets[buyer_name] = w
        
        order['buyer'] = buyer_name
        order['buyer_email'] = buyer_email
        order['status'] = 'matched'
        order['matched_at'] = time.time()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'seller_email': "L'email du vendeur sera révélé après paiement",
            'message': 'Offre acceptée ! Envoyez le paiement PayPal au vendeur pour confirmer'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/p2p/pay', methods=['POST'])
def p2p_confirm_payment():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        buyer_name = d.get('buyer')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'})
        
        order = p2p_orders[order_id]
        
        if order['status'] != 'matched':
            return jsonify({'success': False, 'error': 'Status invalide'})
        
        if order['buyer'] != buyer_name:
            return jsonify({'success': False, 'error': 'Non autorisé'})
        
        order['status'] = 'paid'
        order['paid_at'] = time.time()
        
        seller = active_wallets.get(order['seller'])
        seller_email = getattr(seller, 'email', 'vendeur@veilcoin.com') if seller else 'vendeur@veilcoin.com'
        
        return jsonify({
            'success': True,
            'seller_email': seller_email,
            'amount_eur': order['total_eur'],
            'message': 'Paiement confirmé ! Contactez le vendeur avec l\'email ci-dessus'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/p2p/confirm', methods=['POST'])
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
        else:
            return jsonify({'success': False, 'error': 'Type de confirmation invalide'})
        
        if order['seller_confirmed'] and order['buyer_confirmed']:
            order['status'] = 'completed'
            order['completed_at'] = time.time()
            
            buyer_wallet = active_wallets.get(order['buyer'])
            if buyer_wallet:
                buyer_wallet.balance += order['escrow_veil']
                buyer_wallet.save()
            
            return jsonify({
                'success': True,
                'status': 'completed',
                'message': f'Transaction complétée ! {order["amount_veil"]:.4f} VEIL transférés'
            })
        
        return jsonify({
            'success': True,
            'status': 'waiting',
            'seller_confirmed': order['seller_confirmed'],
            'buyer_confirmed': order['buyer_confirmed'],
            'message': 'En attente de confirmation de l\'autre partie'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/p2p/orders', methods=['GET'])
def p2p_list_orders():
    open_orders = [o for o in p2p_orders.values() if o['status'] == 'open']
    return jsonify({'orders': open_orders, 'count': len(open_orders)})

@app.route('/api/p2p/order/<order_id>', methods=['GET'])
def p2p_get_order(order_id):
    if order_id not in p2p_orders:
        return jsonify({'error': 'Offre introuvable'}), 404
    order = p2p_orders[order_id].copy()
    if order['status'] != 'completed':
        order.pop('seller_email', None)
        order.pop('buyer_email', None)
    return jsonify(order)

# ==================== API STATS ====================

@app.route('/api/stats')
def api_stats():
    if blockchain:
        stats = blockchain.get_stats()
        stats['total_burned'] = total_burned
        stats['burn_percentage'] = (total_burned / MAX_SUPPLY) * 100
        stats['remaining_supply'] = MAX_SUPPLY - total_burned
        return jsonify(stats)
    return jsonify({
        'height': 0, 
        'difficulty': 5, 
        'total_supply': 0, 
        'mempool_size': len(mempool),
        'total_burned': total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100,
        'remaining_supply': MAX_SUPPLY - total_burned
    })

@app.route('/api/blockchain/blocks')
def api_blocks():
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        return jsonify({'blocks': blocks[-20:], 'total': len(blocks)})
    return jsonify({'blocks': [], 'total': 0})

@app.route('/api/market/price')
def api_price():
    if pool:
        return jsonify({
            'current_price': pool.get_veil_price(), 
            'pool_veil': getattr(pool, 'pool_veil', 0), 
            'pool_eur': getattr(pool, 'pool_eur', 0)
        })
    return jsonify({'current_price': 0.042, 'pool_veil': 0, 'pool_eur': 0})

@app.route('/api/market/offers')
def api_offers():
    if pool:
        return jsonify(pool.get_open_sell_offers())
    return jsonify([])

@app.route('/api/pool/info')
def api_pool_info():
    if pool:
        return jsonify(pool.get_pool_info())
    return jsonify({})

@app.route('/api/burn/stats')
def api_burn_stats():
    return jsonify({
        'total_burned': total_burned,
        'total_fees_collected': total_fees_collected,
        'max_supply': MAX_SUPPLY,
        'remaining_supply': MAX_SUPPLY - total_burned,
        'burn_percentage': (total_burned / MAX_SUPPLY) * 100,
        'target_supply': MAX_SUPPLY
    })

# ==================== ADMIN ====================

if not ADMIN_SEED:
    print("⚠️ ATTENTION: ADMIN_SEED non configurée")
    
    @app.route('/api/admin/reset', methods=['POST'])
    def api_admin_reset_disabled():
        return jsonify({'error': 'Admin disabled'}), 503
else:
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
        
        if os.path.exists(MINED_BLOCKS_FILE):
            os.remove(MINED_BLOCKS_FILE)
        
        global mempool, total_burned, total_fees_collected, p2p_orders
        mempool = []
        total_burned = 0
        total_fees_collected = 0
        p2p_orders = {}
        save_burn_stats()
        
        return jsonify({'success': True, 'message': 'Cache vidé. Redémarrage nécessaire.'})

# ==================== PING ====================

@app.route('/ping')
def ping():
    return 'pong', 200

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'blockchain': blockchain is not None,
        'pool': pool is not None,
        'wallets_count': len(active_wallets),
        'mempool_size': len(mempool),
        'total_burned': total_burned,
        'p2p_orders': len(p2p_orders)
    })
