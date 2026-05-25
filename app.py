#!/usr/bin/env python3
"""
VEILCOIN API SERVER - Pour le wallet EXE
"""
import os
import json
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permet au wallet EXE d'appeler l'API

# Stockage temporaire (à remplacer par une vraie BDD plus tard)
wallets_db = {}
balances_db = {}

def generate_address(name):
    """Génère une adresse unique à partir du nom"""
    hash_obj = hashlib.sha256(f"{name}{secrets.token_hex(8)}".encode())
    return f"V{hash_obj.hexdigest()[:40]}"

def generate_seed_phrase():
    """Génère une phrase de 12 mots (version simplifiée)"""
    word_list = ["abandon", "ability", "able", "about", "above", "absent", 
                 "absorb", "abstract", "absurd", "abuse", "access", "accident"]
    return " ".join(secrets.choice(word_list) for _ in range(12))

# ==================== API ROUTES ====================

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet():
    """Crée un nouveau wallet"""
    data = request.get_json()
    name = data.get('name', 'default')
    
    if name in wallets_db:
        return jsonify({"success": False, "error": "Nom déjà utilisé"})
    
    address = generate_address(name)
    seed_phrase = generate_seed_phrase()
    
    wallets_db[name] = {
        "address": address,
        "seed_phrase": seed_phrase,
        "created_at": datetime.now().isoformat()
    }
    balances_db[address] = 100.0  # 100 VEIL de départ (test)
    
    return jsonify({
        "success": True,
        "address": address,
        "seed_phrase": seed_phrase,
        "balance": balances_db[address]
    })

@app.route('/api/wallet/login', methods=['POST'])
def login_wallet():
    """Connecte un wallet existant"""
    data = request.get_json()
    name = data.get('name')
    seed_phrase = data.get('seed_phrase')
    
    if name not in wallets_db:
        return jsonify({"success": False, "error": "Wallet inexistant"})
    
    if wallets_db[name]["seed_phrase"] != seed_phrase:
        return jsonify({"success": False, "error": "Seed phrase incorrecte"})
    
    address = wallets_db[name]["address"]
    
    return jsonify({
        "success": True,
        "address": address,
        "balance": balances_db.get(address, 0),
        "seed_phrase": seed_phrase
    })

@app.route('/api/wallet/<name>/balance', methods=['GET'])
def get_balance(name):
    """Récupère le solde d'un wallet"""
    if name not in wallets_db:
        return jsonify({"error": "Wallet non trouvé"}), 404
    
    address = wallets_db[name]["address"]
    
    return jsonify({
        "balance_veil": balances_db.get(address, 0),
        "address": address
    })

@app.route('/api/wallet/<name>/send', methods=['POST'])
def send_veil(name):
    """Envoie des VEIL à une autre adresse"""
    if name not in wallets_db:
        return jsonify({"success": False, "error": "Wallet non trouvé"})
    
    data = request.get_json()
    to_address = data.get('to')
    amount = float(data.get('amount', 0))
    
    from_address = wallets_db[name]["address"]
    
    # Vérifie le solde
    if balances_db.get(from_address, 0) < amount:
        return jsonify({"success": False, "error": "Solde insuffisant"})
    
    # Effectue le transfert
    balances_db[from_address] -= amount
    balances_db[to_address] = balances_db.get(to_address, 0) + amount
    
    return jsonify({
        "success": True,
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "new_balance": balances_db[from_address]
    })

@app.route('/api/market/price', methods=['GET'])
def market_price():
    """Prix du marché (simulé)"""
    return jsonify({
        "price_usd": 0.042,
        "change_24h": 2.5,
        "volume": 125000
    })

@app.route('/', methods=['GET'])
def home():
    """Page d'accueil simple"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>VeilCoin API</title></head>
    <body>
        <h1>VeilCoin API</h1>
        <p>API active. Utilisez le wallet EXE pour interagir.</p>
        <hr>
        <p>Endpoints disponibles :</p>
        <ul>
            <li>POST /api/wallet/create</li>
            <li>POST /api/wallet/login</li>
            <li>GET /api/wallet/&lt;name&gt;/balance</li>
            <li>POST /api/wallet/&lt;name&gt;/send</li>
            <li>GET /api/market/price</li>
        </ul>
    </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
