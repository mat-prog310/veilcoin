import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from web.app import app, socketio
from config import Config

# Pour Render
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', Config.API_PORT))
    print(f"VeilCoin demarre sur le port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
