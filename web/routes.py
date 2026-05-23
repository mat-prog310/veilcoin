"""
Routes de l'API VeilCoin
"""
from flask import jsonify, request, render_template, session
from web.app import app
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.blockchain import Blockchain
from core.wallet import VeilWallet
from core.randomx_miner import RandomXMiner
from config import Config

# Instances globales
blockchain = Blockchain()
miner = None
active_wallets = {}

# ==================== Pages HTML ====================

@app.route('/')
def index():
    """Dashboard principal"""
    stats = blockchain.get_stats()
    return render_template('index.html', stats=stats)

@app.route('/wallet')
def wallet_page():
    """Page wallet"""
    wallets = list(active_wallets.keys())
    return render_template('wallet.html', wallets=wallets)

@app.route('/miner')
def miner_page():
    """Page du mineur"""
    wallets = list(active_wallets.keys())
    miner_stats = miner.get_stats() if miner else None
    is_mining = miner.is_mining if miner else False
    return render_template('miner.html', 
                         wallets=wallets,
                         miner_stats=miner_stats,
                         is_mining=is_mining)

@app.route('/blockchain')
def blockchain_page():
    """Explorateur de blocs"""
    stats = blockchain.get_stats()
    blocks = blockchain.get_recent_blocks(20)
    return render_template('blockchain.html', stats=stats, blocks=blocks)

@app.route('/explorer')
def explorer_page():
    """Explorateur de transactions"""
    return render_template('explorer.html')

# ==================== API REST ====================

@app.route('/api/stats')
def api_stats():
    """Statistiques blockchain"""
    return jsonify(blockchain.get_stats())

@app.route('/api/blocks')
def api_blocks():
    """Liste des blocs récents"""
    limit = request.args.get('limit', 10, type=int)
    blocks = blockchain.get_recent_blocks(limit)
    return jsonify(blocks)

@app.route('/api/block/<int:height>')
def api_block(height):
    """Bloc par hauteur"""
    block = blockchain.get_block(height=height)
    if block:
        return jsonify(block)
    return jsonify({'error': 'Bloc non trouvé'}), 404

@app.route('/api/transaction/<tx_id>')
def api_transaction(tx_id):
    """Transaction par ID"""
    tx = blockchain.get_transaction(tx_id)
    if tx:
        return jsonify(tx)
    return jsonify({'error': 'Transaction non trouvée'}), 404

@app.route('/api/mempool')
def api_mempool():
    """Transactions en attente"""
    txs = [tx.to_dict() for tx in blockchain.mempool]
    return jsonify(txs)

# ==================== API Wallet ====================

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    """Créer un wallet"""
    data = request.get_json()
    name = data.get('name', 'default')
    
    if name in active_wallets:
        return jsonify({'error': 'Wallet déjà chargé'}), 400
    
    wallet = VeilWallet(name)
    active_wallets[name] = wallet
    return jsonify(wallet.get_info())

@app.route('/api/wallet/load', methods=['POST'])
def api_load_wallet():
    """Charger un wallet existant"""
    data = request.get_json()
    name = data.get('name', 'default')
    
    try:
        wallet = VeilWallet(name)
        active_wallets[name] = wallet
        return jsonify(wallet.get_info())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/wallet/<name>/balance')
def api_wallet_balance(name):
    """Solde du wallet"""
    if name not in active_wallets:
        return jsonify({'error': 'Wallet non trouvé'}), 404
    
    wallet = active_wallets[name]
    balance = blockchain.get_balance(wallet.address)
    wallet.balance = balance
    wallet.save()
    
    return jsonify({
        'name': name,
        'address': wallet.address,
        'balance': balance
    })

@app.route('/api/wallet/<name>/send', methods=['POST'])
def api_send_transaction(name):
    """Envoyer des VEIL"""
    if name not in active_wallets:
        return jsonify({'error': 'Wallet non trouvé'}), 404
    
    data = request.get_json()
    to_address = data.get('to')
    amount = float(data.get('amount', 0))
    
    wallet = active_wallets[name]
    tx = wallet.create_transaction(to_address, amount)
    
    if tx:
        blockchain.add_transaction(tx)
        return jsonify({
            'success': True,
            'tx_id': tx.tx_id,
            'message': f'Transaction {tx.tx_id[:16]}... créée'
        })
    
    return jsonify({'error': 'Échec de la transaction'}), 400

@app.route('/api/wallet/<name>/transactions')
def api_wallet_transactions(name):
    """Transactions du wallet"""
    if name not in active_wallets:
        return jsonify({'error': 'Wallet non trouvé'}), 404
    
    wallet = active_wallets[name]
    txs = wallet.get_recent_transactions(20)
    return jsonify(txs)

# ==================== API Mineur ====================

@app.route('/api/miner/start', methods=['POST'])
def api_start_miner():
    """Démarrer le minage"""
    global miner
    
    data = request.get_json()
    wallet_name = data.get('wallet')
    
    if wallet_name not in active_wallets:
        return jsonify({'error': 'Wallet non trouvé'}), 404
    
    miner = RandomXMiner(blockchain)
    wallet = active_wallets[wallet_name]
    miner.start_mining(wallet.address)
    
    return jsonify({
        'success': True,
        'message': 'Minage démarré',
        'address': wallet.address[:20] + '...'
    })

@app.route('/api/miner/stop')
def api_stop_miner():
    """Arrêter le minage"""
    global miner
    
    if miner:
        miner.stop_mining()
        return jsonify({'success': True, 'message': 'Minage arrêté'})
    
    return jsonify({'error': 'Mineur non actif'}), 400

@app.route('/api/miner/stats')
def api_miner_stats():
    """Statistiques du mineur"""
    if miner:
        return jsonify(miner.get_stats())
    return jsonify({'error': 'Mineur non actif'}), 400

# ==================== API Réseau ====================

@app.route('/api/network/nodes')
def api_network_nodes():
    """Noeuds du réseau"""
    # Simulation pour le moment
    nodes = [
        {'id': 1, 'ip': '127.0.0.1', 'port': 18444, 'status': 'connected'},
        {'id': 2, 'ip': '192.168.1.10', 'port': 18444, 'status': 'connected'},
        {'id': 3, 'ip': '10.0.0.5', 'port': 18444, 'status': 'syncing'}
    ]
    return jsonify(nodes)
