from web.app import app, socketio
import os
from config import Config

if __name__ == '__main__':
    port = int(os.environ.get('PORT', Config.API_PORT))
    print(f"VeilCoin demarre sur le port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
