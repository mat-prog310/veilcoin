"""
Serveur web VeilCoin
"""
from flask import Flask
from flask_socketio import SocketIO
import os
import sys

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

# Créer l'application Flask
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['DEBUG'] = Config.DEBUG

# Initialiser SocketIO pour le temps réel
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Importer les routes après la création de l'app
from web import routes, socket_events
