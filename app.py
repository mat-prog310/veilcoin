from web.app import app as application
from web.app import socketio
import os
from config import Config

if __name__ == '__main__':
    port = int(os.environ.get('PORT', Config.API_PORT))
    socketio.run(application, host='0.0.0.0', port=port, debug=False)
