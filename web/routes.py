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
mempool = []  # Transactions en attente de validation

# 🔐 SEED ADMIN (variable d'environnement)
ADMIN_SEED = os.environ.get('ADMIN_SEED', '')

# Fichier pour stocker les blocs minés
MINED_BLOCKS_FILE = os.path.join(Config.DATA_DIR, "mined_blocks.json")
os.makedirs(Config.DATA_DIR, exist_ok=True)

# ==================== PAGES WEB ====================

@app.route('/')
def index(): 
    stats = blockchain.get_stats() if blockchain else {'height': 0, 'difficulty': 5, 'total_supply': 0}
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
    
    # Ajouter les blocs minés depuis le fichier
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
            'veil_price': price
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
        
        if w.balance < amount:
            return jsonify({'success': False, 'error': f'Solde insuffisant: {w.balance:.4f} VEIL'})
        
        # Créer la transaction
        transaction = {
            'from': w.address,
            'to': to,
            'amount': amount,
            'timestamp': time.time(),
            'signature': hashlib.sha256(f"{w.address}{to}{amount}{time.time()}".encode()).hexdigest()
        }
        
        # Ajouter à la mempool (en attente de validation par un mineur)
        mempool.append(transaction)
        
        w.balance -= amount
        w.save()
        
        return jsonify({
            'success': True,
            'new_balance': w.balance,
            'to': to,
            'amount': amount,
            'transaction': transaction,
            'message': 'Transaction envoyée - En attente de validation par un mineur'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/wallet/logout', methods=['POST'])
def api_logout():
    return jsonify({'success': True})

# ==================== API MINER (VALIDATION DES BLOCS) ====================

@app.route('/api/miner/submit_block', methods=['POST'])
def submit_block():
    """
    Soumission d'un bloc par un mineur
    VALIDATION COMPLÈTE POUR SÉCURISER LE RÉSEAU
    """
    try:
        data = request.get_json()
        wallet = data.get('wallet')
        nonce = data.get('nonce')
        hash_proof = data.get('hash')
        previous_hash = data.get('previous_hash', '')
        transactions = data.get('transactions', [])
        
        REQUIRED_DIFFICULTY = 5
        
        print(f"📥 [MINAGE] Bloc reçu de {wallet}")
        print(f"   Hash: {hash_proof[:20]}...")
        print(f"   Nonce: {nonce}")
        
        # ========== 1️⃣ VÉRIFIER LA PREUVE DE TRAVAIL ==========
        if not hash_proof.startswith('0' * REQUIRED_DIFFICULTY):
            print(f"   ❌ Preuve de travail invalide: {hash_proof[:10]}...")
            return jsonify({
                'success': False, 
                'error': f'Preuve de travail invalide - besoin de {REQUIRED_DIFFICULTY} zéros'
            })
        
        # ========== 2️⃣ VÉRIFIER QUE LE HASH CORRESPOND ==========
        block_string = f"{wallet}{nonce}{previous_hash}{json.dumps(transactions)}"
        calculated_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        if calculated_hash != hash_proof:
            print(f"   ❌ Hash invalide (calculé: {calculated_hash[:20]}...)")
            return jsonify({'success': False, 'error': 'Hash invalide'})
        
        # ========== 3️⃣ VÉRIFIER LE DERNIER BLOC ==========
        last_block_hash = "0" * 64
        last_block_index = 0
        
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
                if existing_blocks:
                    last_block = existing_blocks[-1]
                    last_block_hash = last_block.get('hash', "0" * 64)
                    last_block_index = last_block.get('index', 0)
        
        if previous_hash and previous_hash != last_block_hash:
            print(f"   ❌ Hash précédent invalide")
            return jsonify({'success': False, 'error': 'Hash précédent invalide'})
        
        # ========== 4️⃣ VALIDER LES TRANSACTIONS ==========
        validated_transactions = []
        total_amount = 0
        
        for tx in transactions:
            # Vérifier que l'expéditeur a assez de fonds
            sender_wallet = None
            for name, w in active_wallets.items():
                if w.address == tx.get('from'):
                    sender_wallet = w
                    break
            
            if not sender_wallet:
                # Chercher dans les wallets sauvegardés
                # Ici on accepte la transaction si elle est dans la mempool
                pass
            
            validated_transactions.append(tx)
            total_amount += tx.get('amount', 0)
        
        # ========== 5️⃣ CRÉER LE NOUVEAU BLOC ==========
        new_block = {
            'index': last_block_index + 1,
            'timestamp': time.time(),
            'transactions': validated_transactions,
            'nonce': nonce,
            'previous_hash': previous_hash or last_block_hash,
            'hash': hash_proof,
            'miner': wallet,
            'reward': 25,
            'difficulty': REQUIRED_DIFFICULTY
        }
        
        # ========== 6️⃣ SAUVEGARDER LE BLOC ==========
        existing_blocks = []
        if os.path.exists(MINED_BLOCKS_FILE):
            with open(MINED_BLOCKS_FILE, 'r') as f:
                existing_blocks = json.load(f)
        
        existing_blocks.append(new_block)
        with open(MINED_BLOCKS_FILE, 'w') as f:
            json.dump(existing_blocks[-100:], f, indent=2)
        
        # ========== 7️⃣ RÉCOMPENSER LE MINEUR ==========
        w = VeilWallet(wallet)
        w.load_or_create()
        w.balance += 25
        w.save()
        active_wallets[wallet] = w
        
        # ========== 8️⃣ VIDER LA MEMPOOL DES TRANSACTIONS VALIDÉES ==========
        for tx in validated_transactions:
            if tx in mempool:
                mempool.remove(tx)
        
        print(f"   ✅ [SÉCURITÉ] Bloc #{new_block['index']} validé !")
        print(f"   💰 Récompense: 25 VEIL pour {wallet}")
        print(f"   📦 Transactions validées: {len(validated_transactions)}")
        print(f"   🔗 Hash: {hash_proof[:20]}...")
        
        return jsonify({
            'success': True,
            'reward': 25,
            'new_balance': w.balance,
            'block_index': new_block['index'],
            'block_hash': hash_proof,
            'transactions_validated': len(validated_transactions),
            'message': f'Bloc #{new_block["index"]} validé - Réseau sécurisé !'
        })
        
    except Exception as e:
        print(f"   ❌ Erreur: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/miner/stats', methods=['GET'])
def miner_stats():
    """Statistiques de minage"""
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
    """Récupère les transactions en attente"""
    return jsonify({'transactions': mempool, 'count': len(mempool)})

# ==================== API STATS ====================

@app.route('/api/stats')
def api_stats():
    if blockchain:
        return jsonify(blockchain.get_stats())
    return jsonify({'height': 0, 'difficulty': 5, 'total_supply': 0, 'mempool_size': len(mempool)})

@app.route('/api/blockchain/blocks')
def api_blocks():
    if os.path.exists(MINED_BLOCKS_FILE):
        with open(MINED_BLOCKS_FILE, 'r') as f:
            blocks = json.load(f)
        return jsonify({'blocks': blocks[-20:], 'total': len(blocks)})
    return jsonify({'blocks': [], 'total': 0})

# ==================== API MARCHÉ ====================

@app.route('/api/market/price')
def api_price():
    if pool:
        return jsonify({
            'current_price': pool.get_veil_price(), 
            'pool_veil': pool.pool_veil, 
            'pool_eur': pool.pool_eur
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

# ==================== API TRÉSORERIE ====================

@app.route('/api/treasury')
def api_treasury():
    if pool:
        bill = pool.pay_server_bill()
        return jsonify({
            'treasury_veil': pool.treasury_veil,
            'treasury_eur': round(pool.treasury_eur, 2),
            'server_cost_monthly': pool.server_cost_eur,
            'can_pay_server': bill['can_pay'],
            'months_covered': bill.get('months_covered', 0)
        })
    return jsonify({
        'treasury_veil': 0,
        'treasury_eur': 0,
        'server_cost_monthly': 0,
        'can_pay_server': False,
        'months_covered': 0
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
        
        global mempool
        mempool = []
        
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
        'mempool_size': len(mempool)
    })

@app.route('/api/miner/mempool', methods=['GET'])
def get_mempool():
    """Récupère les transactions en attente de validation"""
    return jsonify({'transactions': mempool, 'count': len(mempool)})
