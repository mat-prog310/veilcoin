"""
Événements Socket.IO pour le temps réel
"""
import time
import threading
from web.app import socketio, app
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.routes import blockchain, miner

# Thread pour les mises à jour en temps réel
update_thread = None
update_running = False

def background_stats_updater():
    """Thread qui envoie les stats toutes les 2 secondes"""
    global update_running
    
    while update_running:
        try:
            # Stats blockchain
            stats = blockchain.get_stats()
            socketio.emit('blockchain_stats', stats)
            
            # Stats mineur
            if miner and miner.is_mining:
                miner_stats = miner.get_stats()
                socketio.emit('miner_stats', miner_stats)
            
            # Derniers blocs
            recent_blocks = blockchain.get_recent_blocks(5)
            socketio.emit('recent_blocks', recent_blocks)
            
            # Mempool
            mempool = [tx.to_dict() for tx in blockchain.mempool]
            socketio.emit('mempool_update', {'count': len(mempool), 'transactions': mempool[:10]})
            
            time.sleep(2)
        except Exception as e:
            print(f"Erreur mise à jour: {e}")
            time.sleep(5)

@socketio.on('connect')
def handle_connect():
    """Client connecté"""
    print(f"Client connecté: {socketio.server.manager}")
    global update_running, update_thread
    
    if not update_running:
        update_running = True
        update_thread = threading.Thread(target=background_stats_updater, daemon=True)
        update_thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    """Client déconnecté"""
    print("Client déconnecté")

@socketio.on('request_stats')
def handle_stats_request():
    """Demande de stats"""
    stats = blockchain.get_stats()
    socketio.emit('blockchain_stats', stats)
    
    if miner:
        socketio.emit('miner_stats', miner.get_stats())

@socketio.on('mine_block')
def handle_mine_block(data):
    """Miner un bloc manuellement"""
    wallet_name = data.get('wallet')
    from web.routes import active_wallets
    
    if wallet_name in active_wallets:
        wallet = active_wallets[wallet_name]
        
        if miner:
            block = miner.mine_block(wallet.address)
            if block:
                socketio.emit('block_mined', {
                    'success': True,
                    'block': block.to_dict(),
                    'reward': blockchain.calculate_block_reward()
                })
            else:
                socketio.emit('block_mined', {'success': False, 'error': 'Échec du minage'})
