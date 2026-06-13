# web/blueprint.py
from flask import Blueprint, jsonify, request, render_template
import sys, os
import hashlib
import time
import json
from datetime import datetime
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wallet import VeilWallet
from core.market import VeilMarket
from core.payment import LiquidityPool
from config import Config
import base64

web_bp = Blueprint('web', __name__, template_folder='../templates')

@web_bp.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

# ==================== SÉCURITÉ EXTREME ====================

# 1. LIMITATION IP (1 wallet par IP)
used_ips = {}  # ip -> wallet
used_fingerprints = {}  # fingerprint -> wallet
banned_fingerprints = set()
ip_request_count = {}
RATE_LIMIT_PER_IP = 100
FINGERPRINT_RATE_LIMIT = 10

# 2. ANTI-FERME MINAGE
mining_sessions = {}
MINING_RATE_LIMIT = 3  # 3 blocs par heure max
MINING_SESSION_DURATION = 3600
MINING_COOLDOWN = 3600

# 3. PRIX MINIMUM
ABSOLUTE_MIN_PRICE = 0.01
MAX_VEIL_PER_ORDER = 10000

# 4. WHITELIST ADMIN
ADMIN_IPS = [
    "10.24.250.132",
    "10.31.93.2",
    "10.25.168.6",
    "10.28.13.134",
    "127.0.0.1"
]
ADMIN_WALLETS = ["dev", "treasury"]

# ==================== FONCTIONS SÉCURITÉ ====================

def is_admin_ip(ip):
    return ip in ADMIN_IPS

def is_admin_wallet(wallet):
    return wallet in ADMIN_WALLETS

def check_rate_limit(ip):
    now = time.time()
    if ip not in ip_request_count:
        ip_request_count[ip] = {"count": 1, "reset_time": now + 3600}
        return True
    data = ip_request_count[ip]
    if now > data["reset_time"]:
        data["count"] = 1
        data["reset_time"] = now + 3600
        return True
    if data["count"] >= RATE_LIMIT_PER_IP:
        return False
    data["count"] += 1
    return True

def check_fingerprint_rate_limit(fingerprint):
    now = time.time()
    if fingerprint not in ip_request_count:
        ip_request_count[fingerprint] = [now]
        return True
    ip_request_count[fingerprint] = [t for t in ip_request_count[fingerprint] if now - t < 60]
    if len(ip_request_count[fingerprint]) >= FINGERPRINT_RATE_LIMIT:
        return False
    ip_request_count[fingerprint].append(now)
    return True

def is_fingerprint_banned(fingerprint):
    return fingerprint in banned_fingerprints

def get_difficulty():
    """Ajuste la difficulté pour ~1 bloc par heure"""
    MINED_BLOCKS_FILE = os.path.join(DATA_DIR, "mined_blocks.json")
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        if len(blocks) > 10:
            last_10 = blocks[-10:]
            times = []
            for i in range(1, len(last_10)):
                diff = last_10[i].get('timestamp', 0) - last_10[i-1].get('timestamp', 0)
                if diff > 0:
                    times.append(diff)
            if times:
                avg_time = sum(times) / len(times)
                if avg_time < 3500:
                    return 6
                elif avg_time < 3000:
                    return 7
                elif avg_time < 2500:
                    return 8
                elif avg_time < 2000:
                    return 9
    return 5

def check_mining_farm(wallet_address):
    """Vérifie si un wallet est une ferme de minage"""
    now = time.time()
    session = mining_sessions.get(wallet_address, {})
    
    if is_mining_banned(wallet_address):
        return False, "❌ Wallet banni du minage"
    
    blocks_mined = session.get('blocks_mined', 0)
    last_block_time = session.get('last_block_time', 0)
    
    if blocks_mined >= MINING_RATE_LIMIT:
        time_since_last = now - last_block_time
        if time_since_last < MINING_SESSION_DURATION:
            remaining = int((MINING_SESSION_DURATION - time_since_last) / 60)
            return False, f"❌ Limite de {MINING_RATE_LIMIT} blocs/heure. Attendez {remaining} minutes."
    
    session_end = session.get('session_end', 0)
    if now < session_end:
        remaining = int((session_end - now) / 60)
        return False, f"❌ Cooldown actif. Réessayez dans {remaining} minutes."
    
    return True, "OK"

def update_mining_session(wallet_address):
    now = time.time()
    session = mining_sessions.get(wallet_address, {'blocks_mined': 0})
    session['blocks_mined'] = session.get('blocks_mined', 0) + 1
    session['last_block_time'] = now
    if session['blocks_mined'] >= MINING_RATE_LIMIT:
        session['session_end'] = now + MINING_COOLDOWN
    mining_sessions[wallet_address] = session

# ==================== MIDDLEWARE SÉCURITÉ ====================

@web_bp.before_request
def security_middleware():
    client_ip = request.remote_addr
    if is_admin_ip(client_ip):
        return None
    if is_ip_banned(client_ip):
        return jsonify({'error': 'ACCESS_DENIED', 'code': 'IP_BANNED'}), 403
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'RATE_LIMIT_EXCEEDED'}), 429
    return None

# ==================== BLACKLIST ====================
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")
MINING_BLACKLIST_FILE = os.path.join(DATA_DIR, "mining_blacklist.json")
IP_BLACKLIST_FILE = os.path.join(DATA_DIR, "ip_blacklist.json")

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    return {'wallets': [], 'ips': [], 'users': []}

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist, f, indent=2)

def load_mining_blacklist():
    if os.path.exists(MINING_BLACKLIST_FILE):
        with open(MINING_BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    return {'wallets': [], 'reasons': {}}

def save_mining_blacklist(blacklist):
    with open(MINING_BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist, f, indent=2)

def is_mining_banned(wallet_address):
    blacklist = load_mining_blacklist()
    return wallet_address in blacklist['wallets']

def ban_from_mining(wallet_address, reason):
    blacklist = load_mining_blacklist()
    if wallet_address not in blacklist['wallets']:
        blacklist['wallets'].append(wallet_address)
        blacklist['reasons'][wallet_address] = reason
        save_mining_blacklist(blacklist)
        print(f"⛔ MINING BAN: {wallet_address} - {reason}")
        return True
    return False

def load_ip_blacklist():
    if os.path.exists(IP_BLACKLIST_FILE):
        with open(IP_BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    return {'ips': [], 'reasons': {}, 'permanent': []}

def save_ip_blacklist(blacklist):
    with open(IP_BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist, f, indent=2)

def is_ip_banned(client_ip):
    blacklist = load_ip_blacklist()
    return client_ip in blacklist['ips']

def ban_ip_address(ip_address, reason, permanent=True):
    blacklist = load_ip_blacklist()
    if ip_address not in blacklist['ips']:
        blacklist['ips'].append(ip_address)
        blacklist['reasons'][ip_address] = reason
        if permanent:
            blacklist['permanent'].append(ip_address)
        save_ip_blacklist(blacklist)
        print(f"🚫 IP BAN: {ip_address} - {reason}")
        return True
    return False

def unban_ip_address(ip_address):
    blacklist = load_ip_blacklist()
    if ip_address in blacklist['ips']:
        blacklist['ips'].remove(ip_address)
        if ip_address in blacklist['reasons']:
            del blacklist['reasons'][ip_address]
        if ip_address in blacklist['permanent']:
            blacklist['permanent'].remove(ip_address)
        save_ip_blacklist(blacklist)
        return True
    return False

# ==================== IMPORT MODULES ====================
from core.reputation import ReputationSystem
from core.secure_storage import SecureStorage

reputation = ReputationSystem(DATA_DIR)
secure_storage = SecureStorage(DATA_DIR)

# ==================== P2P ====================
P2P_ORDERS_FILE = os.path.join(DATA_DIR, "p2p_orders.json")
p2p_orders = {}
p2p_counter = 0

def load_p2p_orders():
    global p2p_orders, p2p_counter
    if os.path.exists(P2P_ORDERS_FILE):
        try:
            with open(P2P_ORDERS_FILE, 'r') as f:
                data = json.load(f)
                p2p_orders = data.get('orders', {})
                p2p_counter = data.get('counter', 0)
                print(f"📦 Chargé {len(p2p_orders)} offres P2P")
        except:
            p2p_orders = {}
            p2p_counter = 0
    else:
        p2p_orders = {}
        p2p_counter = 0
    load_p2p_orders()

def save_p2p_orders():
    with open(P2P_ORDERS_FILE, 'w') as f:
        json.dump({'orders': p2p_orders, 'counter': p2p_counter}, f, indent=2)

# ==================== PRIX ====================

def get_current_price():
    completed_orders = [o for o in p2p_orders.values() if o['status'] == 'completed']
    filtered = [o for o in completed_orders if o.get('amount_veil', 0) >= 10]
    if not filtered:
        return 0.02
    last_10 = filtered[-10:]
    total_value = sum(o['total_eur'] for o in last_10)
    total_veil = sum(o['amount_veil'] for o in last_10)
    if total_veil <= 0:
        return 0.02
    price = total_value / total_veil
    if hasattr(get_current_price, 'last_price'):
        max_change = get_current_price.last_price * 0.10
        if price > get_current_price.last_price + max_change:
            price = get_current_price.last_price + max_change
        elif price < get_current_price.last_price - max_change:
            price = get_current_price.last_price - max_change
    get_current_price.last_price = price
    return round(price, 6)

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

@web_bp.route('/api/set-fingerprint', methods=['POST'])
def set_fingerprint():
    fingerprint = request.headers.get('X-Device-Fingerprint', '')
    if fingerprint:
        request.environ['device_fingerprint'] = fingerprint
    return jsonify({'success': True})

@web_bp.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    try:
        client_ip = request.remote_addr
        fingerprint = request.headers.get('X-Device-Fingerprint', '')
        
        if is_fingerprint_banned(fingerprint):
            return jsonify({'success': False, 'error': '❌ Appareil banni'}), 403
        
        if fingerprint and not check_fingerprint_rate_limit(fingerprint):
            return jsonify({'success': False, 'error': '❌ Trop de tentatives'}), 429
        
        if fingerprint and fingerprint in used_fingerprints:
            existing = used_fingerprints[fingerprint]
            return jsonify({'success': False, 'error': f'❌ Un wallet existe déjà sur cet appareil ({existing})'}), 403
        
        if not is_admin_ip(client_ip) and client_ip in used_ips:
            return jsonify({'success': False, 'error': '❌ 1 wallet par personne maximum'}), 403
        
        d = request.get_json(silent=True) or {}
        name = d.get('name', 'default').strip()
        
        wallet_path = os.path.join(DATA_DIR, "wallets", f"{name}.json")
        if os.path.exists(wallet_path):
            return jsonify({'success': False, 'error': '❌ Ce nom de wallet existe déjà'}), 400
        
        w = VeilWallet(name)
        r = w.create_new()
        active_wallets[name] = w
        
        if fingerprint and not is_admin_ip(client_ip):
            used_fingerprints[fingerprint] = name
        if not is_admin_ip(client_ip):
            used_ips[client_ip] = name
        
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

# ==================== API MINER (ACTIF AVEC SÉCURITÉ) ====================

@web_bp.route('/api/miner/submit_block', methods=['POST'])
def submit_block():
    try:
        data = request.get_json()
        wallet = data.get('wallet')
        nonce = data.get('nonce')
        hash_proof = data.get('hash')
        transactions = data.get('transactions', [])
        client_ip = request.remote_addr
        
        # ===== ANTI-FERME MINAGE =====
        can_mine, msg = check_mining_farm(wallet)
        if not can_mine:
            return jsonify({'success': False, 'error': msg}), 429
        
        # Vérifier que le wallet existe
        w = VeilWallet(wallet)
        if not w.load_or_create():
            return jsonify({'success': False, 'error': 'Wallet invalide'}), 400
        
        # Vérifier la preuve de travail avec difficulté dynamique
        difficulty = get_difficulty()
        required_prefix = '0' * difficulty
        if not hash_proof.startswith(required_prefix):
            return jsonify({'success': False, 'error': f'Preuve invalide (difficulté: {difficulty})'}), 400
        
        # Vérifier IP bannie
        if is_ip_banned(client_ip):
            return jsonify({'error': 'IP_BANNED'}), 403
        
        # Vérifier ban minage
        if is_mining_banned(wallet):
            ban_ip_address(client_ip, f"Auto-ban - Wallet {wallet} mining attempt while banned", permanent=True)
            return jsonify({'success': False, 'error': '❌ Wallet banni du minage'}), 403
        
        # Récupérer les blocs existants
        existing_blocks = []
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
        
        # Limite par wallet (1000 blocs max à vie)
        MAX_BLOCKS_PER_WALLET = 1000
        user_blocks = [b for b in existing_blocks if b.get('miner') == wallet]
        if len(user_blocks) >= MAX_BLOCKS_PER_WALLET:
            return jsonify({'success': False, 'error': f'❌ Limite atteinte ! Maximum {MAX_BLOCKS_PER_WALLET} blocs'}), 403
        
        last_index = existing_blocks[-1].get('index', 0) if existing_blocks else 0
        last_hash = existing_blocks[-1].get('hash', '0'*64) if existing_blocks else '0'*64
        
        new_block = {
            'index': last_index + 1,
            'timestamp': time.time(),
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': last_hash,
            'hash': hash_proof,
            'miner': wallet,
            'reward_miner': 50,
            'reward_pool': 0,
            'difficulty': difficulty
        }
        
        existing_blocks.append(new_block)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks[-100:], f, indent=2)
        
        # Récompense
        w.balance += 50
        w.save()
        active_wallets[wallet] = w
        
        # Mettre à jour la session de minage
        update_mining_session(wallet)
        
        blocks_left_this_hour = max(0, MINING_RATE_LIMIT - mining_sessions.get(wallet, {}).get('blocks_mined', 0))
        
        return jsonify({
            'success': True,
            'reward_miner': 50,
            'new_balance': w.balance,
            'block_index': new_block['index'],
            'difficulty': difficulty,
            'blocks_left_this_hour': blocks_left_this_hour,
            'message': f'✅ Bloc #{new_block["index"]} miné ! Plus que {blocks_left_this_hour} blocs cette heure'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@web_bp.route('/api/miner/getmine', methods=['GET'])
def getmine():
    return submit_block()

@web_bp.route('/api/miner/status', methods=['GET'])
def miner_status():
    return jsonify({
        'mining_enabled': True,
        'staking_required': 0,
        'rate_limit': MINING_RATE_LIMIT,
        'cooldown': MINING_COOLDOWN,
        'message': f'{MINING_RATE_LIMIT} blocs/heure maximum'
    })

@web_bp.route('/api/miner/farm_status', methods=['GET'])
def farm_status():
    wallet = request.args.get('wallet')
    if not wallet:
        return jsonify({'error': 'Wallet requis'}), 400
    
    session = mining_sessions.get(wallet, {})
    now = time.time()
    blocks_mined = session.get('blocks_mined', 0)
    blocks_left = max(0, MINING_RATE_LIMIT - blocks_mined)
    cooldown_left = max(0, session.get('session_end', 0) - now)
    
    return jsonify({
        'wallet': wallet,
        'blocks_mined_this_hour': blocks_mined,
        'blocks_left_this_hour': blocks_left,
        'max_per_hour': MINING_RATE_LIMIT,
        'cooldown_seconds': int(cooldown_left),
        'cooldown_minutes': int(cooldown_left / 60),
        'can_mine': blocks_left > 0 and cooldown_left == 0
    })

@web_bp.route('/api/miner/user_blocks', methods=['GET'])
def get_user_blocks():
    wallet = request.args.get('wallet')
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
            user_blocks = [b for b in blocks if b.get('miner') == wallet]
            return jsonify({'mined': len(user_blocks), 'max': 10000})
    return jsonify({'mined': 0, 'max': 10000})

@web_bp.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'transactions': mempool, 'count': len(mempool)})

@web_bp.route('/api/miner/user_stats', methods=['GET'])
def get_user_stats():
    wallet = request.args.get('wallet')
    MAX_BLOCKS_PER_WALLET = 1000
    
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
            user_blocks = [b for b in blocks if b.get('miner') == wallet]
            return jsonify({
                'blocks_mined': len(user_blocks),
                'blocks_left': max(0, MAX_BLOCKS_PER_WALLET - len(user_blocks)),
                'max_blocks': MAX_BLOCKS_PER_WALLET
            })
    return jsonify({'blocks_mined': 0, 'blocks_left': MAX_BLOCKS_PER_WALLET, 'max_blocks': MAX_BLOCKS_PER_WALLET})

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
        client_ip = request.remote_addr
        
        current_price = get_current_price()
        max_price = current_price * 1.50
        min_price = current_price * 0.50
        
        if price_eur < ABSOLUTE_MIN_PRICE:
            return jsonify({'success': False, 'error': f'❌ Prix minimum: {ABSOLUTE_MIN_PRICE}€'}), 403
        
        if price_eur > max_price:
            return jsonify({'success': False, 'error': f'❌ Prix trop élevé ! Max {max_price:.4f}€'}), 403
        
        if price_eur < min_price:
            return jsonify({'success': False, 'error': f'❌ Prix trop bas ! Min {min_price:.4f}€'}), 403
        
        if amount_veil > MAX_VEIL_PER_ORDER:
            return jsonify({'success': False, 'error': f'❌ Maximum {MAX_VEIL_PER_ORDER} VEIL par offre'}), 403
        
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
            'id': order_id, 'seller': wallet_name, 'seller_email': seller_email,
            'amount_veil': amount_veil, 'price_eur': price_eur,
            'total_eur': amount_veil * price_eur, 'status': 'open',
            'buyer': None, 'buyer_email': None, 'seller_ip': client_ip,
            'created_at': time.time()
        }
        
        save_p2p_orders()
        return jsonify({'success': True, 'order_id': order_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/orders', methods=['GET'])
def p2p_list_orders():
    open_orders = [o for o in p2p_orders.values() if o['status'] == 'open']
    return jsonify({'orders': open_orders, 'count': len(open_orders)})

@web_bp.route('/api/p2p/my-orders', methods=['GET'])
def p2p_my_orders():
    wallet = request.args.get('wallet')
    if not wallet:
        return jsonify({'orders': [], 'count': 0})
    my_orders = [o for o in p2p_orders.values() if o.get('seller') == wallet or o.get('buyer') == wallet]
    return jsonify({'orders': my_orders, 'count': len(my_orders)})

@web_bp.route('/api/p2p/history', methods=['GET'])
def p2p_history():
    completed_orders = [o for o in p2p_orders.values() if o['status'] == 'completed']
    anonymized = [{
        'timestamp': o.get('completed_at', o.get('created_at', time.time())),
        'amount_veil': o['amount_veil'], 'price_eur': o['price_eur'], 'total_eur': o['total_eur']
    } for o in completed_orders]
    anonymized.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify({'transactions': anonymized, 'count': len(anonymized)})

@web_bp.route('/api/p2p/match', methods=['POST'])
def p2p_match_order():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        buyer_name = d.get('buyer')
        buyer_email = d.get('email')
        client_ip = request.remote_addr
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'}), 404
        
        order = p2p_orders[order_id]
        
        if order['seller'] == buyer_name:
            return jsonify({'success': False, 'error': '❌ Impossible d\'acheter ses propres VEIL'}), 403
        
        seller_ip = order.get('seller_ip')
        if seller_ip and seller_ip == client_ip:
            return jsonify({'success': False, 'error': '❌ Même IP que le vendeur'}), 403
        
        if order.get('seller_email') == buyer_email:
            return jsonify({'success': False, 'error': '❌ Email déjà utilisé par le vendeur'}), 403
        
        if order['status'] != 'open':
            return jsonify({'success': False, 'error': 'Offre déjà prise'}), 400
        
        order['buyer'] = buyer_name
        order['buyer_email'] = buyer_email
        order['buyer_ip'] = client_ip
        order['status'] = 'matched'
        
        save_p2p_orders()
        
        return jsonify({
            'success': True, 'order_id': order_id, 
            'seller_email': order.get('seller_email'),
            'amount_eur': order['total_eur']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/pay', methods=['POST'])
def p2p_confirm_payment():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        buyer_name = d.get('buyer')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'}), 404
        
        order = p2p_orders[order_id]
        
        if order['status'] != 'matched' or order['buyer'] != buyer_name:
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        
        order['status'] = 'pending_proof'
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Paiement confirmé'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/release', methods=['POST'])
def p2p_release_veil():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        seller_name = d.get('seller')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'}), 404
        
        order = p2p_orders[order_id]
        
        if order['seller'] != seller_name:
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        
        if order['status'] != 'paid':
            return jsonify({'success': False, 'error': 'Paiement non confirmé'}), 400
        
        buyer_wallet = VeilWallet(order['buyer'])
        buyer_wallet.load_or_create()
        buyer_wallet.balance += order['amount_veil']
        buyer_wallet.save()
        
        order['status'] = 'completed'
        order['completed_at'] = time.time()
        save_p2p_orders()
        
        return jsonify({'success': True, 'amount_veil': order['amount_veil']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/p2p/accept_proof', methods=['POST'])
def accept_proof():
    try:
        d = request.get_json()
        order_id = d.get('order_id')
        seller_name = d.get('seller')
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'}), 404
        
        order = p2p_orders[order_id]
        
        if order.get('seller') != seller_name:
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        
        if not order.get('payment_proof'):
            return jsonify({'success': False, 'error': 'Aucune preuve reçue'}), 400
        
        order['status'] = 'paid'
        order['seller_confirmed'] = True
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Preuve acceptée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== PREUVE DE PAIEMENT ====================

PROOF_DIR = os.path.join(DATA_DIR, "payment_proofs")
os.makedirs(PROOF_DIR, exist_ok=True)

@web_bp.route('/api/upload/proof', methods=['POST'])
def upload_proof():
    try:
        order_id = request.form.get('order_id')
        buyer_name = request.form.get('buyer')
        file = request.files.get('proof')
        
        if not file:
            return jsonify({'success': False, 'error': 'Aucun fichier'}), 400
        
        if order_id not in p2p_orders:
            return jsonify({'success': False, 'error': 'Offre introuvable'}), 404
        
        order = p2p_orders[order_id]
        
        if order.get('buyer') != buyer_name:
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        
        filename = f"{order_id}_{int(time.time())}.txt"
        image_data = base64.b64encode(file.read()).decode('utf-8')
        
        proof_path = os.path.join(PROOF_DIR, filename)
        with open(proof_path, 'w') as f:
            f.write(image_data)
        
        order['payment_proof'] = filename
        order['proof_uploaded'] = True
        save_p2p_orders()
        
        return jsonify({'success': True, 'message': 'Preuve envoyée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@web_bp.route('/api/p2p/view_proof/<filename>', methods=['GET'])
def view_proof(filename):
    try:
        wallet = request.args.get('wallet')
        proof_path = os.path.join(PROOF_DIR, filename)
        
        if not os.path.exists(proof_path):
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        with open(proof_path, 'r') as f:
            proof = f.read()
        
        return jsonify({'success': True, 'proof': proof})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ADMIN ====================

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
            return jsonify({'error': 'Non autorisé'}), 401
        
        from_w = VeilWallet(from_wallet)
        from_w.load_or_create()
        to_w = VeilWallet(to_wallet)
        to_w.load_or_create()
        
        if from_w.balance < amount:
            return jsonify({'success': False, 'error': 'Solde insuffisant'}), 400
        
        from_w.balance -= amount
        to_w.balance += amount
        from_w.save()
        to_w.save()
        
        return jsonify({'success': True, 'message': f'{amount} VEIL transférés'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/ban_fingerprint', methods=['POST'])
def admin_ban_fingerprint():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        fingerprint = d.get('fingerprint')
        reason = d.get('reason', 'Violation')
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 401
        
        if fingerprint:
            banned_fingerprints.add(fingerprint)
            if fingerprint in used_fingerprints:
                wallet = used_fingerprints[fingerprint]
                ban_from_mining(wallet, reason)
            return jsonify({'success': True, 'message': 'Fingerprint banni'})
        return jsonify({'error': 'Fingerprint requis'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/unban_wallet', methods=['POST'])
def admin_unban_wallet():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        wallet_name = d.get('wallet')
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 401
        
        blacklist = load_blacklist()
        if wallet_name in blacklist['wallets']:
            blacklist['wallets'].remove(wallet_name)
        save_blacklist(blacklist)
        
        return jsonify({'success': True, 'message': f'Wallet {wallet_name} débanni'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/ban_ip', methods=['POST'])
def admin_ban_ip():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        ip = d.get('ip')
        reason = d.get('reason', 'Violation')
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 401
        
        ban_ip_address(ip, reason, permanent=True)
        return jsonify({'success': True, 'message': f'IP {ip} bannie'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/unban_ip', methods=['POST'])
def admin_unban_ip():
    try:
        d = request.get_json()
        admin_seed = d.get('admin_seed', '')
        ip = d.get('ip')
        
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 401
        
        unban_ip_address(ip)
        return jsonify({'success': True, 'message': f'IP {ip} débannie'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@web_bp.route('/api/admin/ip_blacklist', methods=['GET'])
def admin_ip_blacklist():
    try:
        admin_seed = request.args.get('admin_seed', '')
        ADMIN_SEED = os.environ.get('ADMIN_SEED', '')
        if admin_seed != ADMIN_SEED:
            return jsonify({'error': 'Non autorisé'}), 401
        
        blacklist = load_ip_blacklist()
        return jsonify({
            'banned_ips': blacklist['ips'],
            'reasons': blacklist['reasons'],
            'count': len(blacklist['ips'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== STATS ====================

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
    return jsonify({'status': 'ok'})

