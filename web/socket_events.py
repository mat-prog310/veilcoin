import time, threading
from web.app import socketio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

update_running = False

def updater():
    global update_running
    while update_running:
        try:
            from web.routes import blockchain, miner
            socketio.emit('blockchain_stats', blockchain.get_stats())
            if miner and miner.is_mining:
                socketio.emit('miner_stats', miner.get_stats())
            socketio.emit('recent_blocks', blockchain.get_recent_blocks(5))
        except Exception as e:
            print(f"Socket error: {e}")
        time.sleep(2)

@socketio.on('connect')
def connect():
    global update_running
    if not update_running:
        update_running = True
        threading.Thread(target=updater, daemon=True).start()
