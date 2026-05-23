#!/usr/bin/env python3
"""
VeilCoin - Interface Web
Lance le serveur Flask avec Socket.IO
"""
import sys
import os
import webbrowser
from threading import Timer

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app, socketio
from config import Config

def open_browser():
    """Ouvre le navigateur automatiquement"""
    webbrowser.open(f'http://localhost:{Config.API_PORT}')

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║     🌫️  VEILCOIN - Interface Web  🌫️          ║
    ║     Mine Simply. Transact Privately.         ║
    ╚══════════════════════════════════════════════╝
    """)
    
    print(f"🚀 Serveur démarré sur http://localhost:{Config.API_PORT}")
    print(f"📊 Dashboard : http://localhost:{Config.API_PORT}")
    print(f"👛 Wallet : http://localhost:{Config.API_PORT}/wallet")
    print(f"⛏️  Mineur : http://localhost:{Config.API_PORT}/miner")
    print(f"🔗 Explorer : http://localhost:{Config.API_PORT}/blockchain")
    print("\n⚠️  Appuyez sur Ctrl+C pour arrêter le serveur\n")
    
    # Ouvrir le navigateur après 1 seconde
    Timer(1, open_browser).start()
    
    # Lancer le serveur
    socketio.run(app, 
                host='0.0.0.0', 
                port=Config.API_PORT, 
                debug=Config.DEBUG,
                allow_unsafe_werkzeug=True)
