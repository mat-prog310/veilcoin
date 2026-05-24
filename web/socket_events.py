import time
import threading
from web.app import socketio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from web.routes import blockchain, miner

update_running = False

def updater():
    while update_running:
        try:
            stats = blockchain.get_stats()
            socketio.emit('blockchain_stats', stats)
            
            if miner and miner.is_mining:
                socketio.emit('miner_stats', miner.get_stats())
            
            recent_blocks = blockchain.get_recent_blocks(5)
            socketio.emit('recent_blocks', recent_blocks)
        except Exception as e:
            print(f"Erreur socket: {e}")
        time.sleep(2)

@socketio.on('connect')
def connect():
    global update_running
    if not update_running:
        update_running = True
        threading.Thread(target=updater, daemon=True).start()
        print("✅ Client connecté - Stats en temps réel activées")

@socketio.on('disconnect')
def disconnect():
    print("Client déconnecté")
