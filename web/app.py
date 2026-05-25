# web/app.py
from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from web.blueprint import web_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'veilcoin-secret-key')
    # Enregistrer le blueprint
    app.register_blueprint(web_bp)
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
