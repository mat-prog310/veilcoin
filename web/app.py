# web/app.py - VERSION CORRIGÉE (sans socket_events)

from flask import Flask
from flask_cors import CORS
import os

# Import des routes uniquement (pas socket_events)
from web import routes

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-veilcoin')
    
    # Pas de socketio.init_app(app) ici
    
    return app

# Créer l'instance
app = create_app()

# Enregistrer les routes (si nécessaire)
# Les routes sont déjà importées via 'from web import routes'
