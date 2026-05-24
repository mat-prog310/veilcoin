from flask import Flask
from flask_socketio import SocketIO
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['DEBUG'] = False

# Threading marche partout, pas besoin de gevent/eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

from web import routes, socket_events
