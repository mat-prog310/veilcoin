from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'veilcoin-secret-key')
    return app

# Créer l'instance
app = create_app()

# Importer les routes APRÈS la création de l'app
from web import routes

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
