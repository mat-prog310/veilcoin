#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    ⛏️  VEILCOIN MINER  ⛏️                     ║
║                                                              ║
║  Mine Simply. Transact Privately.                            ║
║                                                              ║
║  Version: 1.0.0                                              ║
║  Algorithme: SHA256 Proof of Work                            ║
║  Récompense: 50 VEIL / bloc                                  ║
║  Supply Max: 25 000 000 VEIL                                 ║
╚══════════════════════════════════════════════════════════════╝
"""
import hashlib
import time
import threading
import os
import sys
import requests
from datetime import datetime

# ==================== CONFIGURATION ====================

API_URL = "https://veilcoin-fvzp.onrender.com"  # Change si nécessaire
WALLET_NAME = ""
WALLET_SEED = ""

# Couleurs terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
PURPLE = "\033[95m"
WHITE = "\033[97m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ==================== ASCII ART ====================

BANNER = f"""
{PURPLE}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██╗   ██╗███████╗██╗██╗      ██████╗ ██████╗ ██╗███╗   ██╗
║   ██║   ██║██╔════╝██║██║     ██╔════╝██╔═══██╗██║████╗  ██║
║   ██║   ██║█████╗  ██║██║     ██║     ██║   ██║██║██╔██╗ ██║
║   ╚██╗ ██╔╝██╔══╝  ██║██║     ██║     ██║   ██║██║██║╚██╗██║
║    ╚████╔╝ ███████╗██║███████╗╚██████╗╚██████╔╝██║██║ ╚████║
║     ╚═══╝  ╚══════╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝
║                                                              ║
║                  {YELLOW}⛏️  MINER TERMINAL  ⛏️{RESET}                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{RESET}
"""

# ==================== MINER ====================

class MinerStats:
    def __init__(self):
        self.hashrate = 0
        self.total_hashes = 0
        self.blocks_mined = 0
        self.shares = 0
        self.start_time = 0

class VeilMiner:
    def __init__(self, api_url, wallet_name):
        self.api_url = api_url
        self.wallet_name = wallet_name
        self.is_mining = False
        self.stats = MinerStats()
        self.difficulty = 3
        self.target = "0" * self.difficulty
        self.balance = 0.0
        
    def login(self, seed):
        """Se connecter au wallet"""
        print(f"{CYAN}[*] Connexion au wallet {self.wallet_name}...{RESET}")
        try:
            res = requests.post(f"{self.api_url}/api/wallet/login", json={
                "name": self.wallet_name,
                "seed_phrase": seed
            })
            data = res.json()
            if data.get("success"):
                self.balance = data.get("balance", 0)
                print(f"{GREEN}[✓] Connecté ! Solde: {self.balance:.4f} VEIL{RESET}")
                return True
            else:
                print(f"{RED}[✗] Erreur: {data.get('error', 'Inconnue')}{RESET}")
                return False
        except Exception as e:
            print(f"{RED}[✗] Erreur connexion: {e}{RESET}")
            return False
    
    def start(self):
        """Démarrer le minage"""
        print(f"\n{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}🔒 DÉMARRAGE DU MINAGE{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}")
        print(f"  🎯 Cible: {self.target}...")
        print(f"  📊 Difficulté: {self.difficulty}")
        print(f"  💰 Récompense: 50 VEIL/bloc")
        print(f"  🛡️  Algorithme: SHA256 Proof of Work")
        print(f"{YELLOW}{'='*60}{RESET}\n")
        
        self.is_mining = True
        self.stats.start_time = time.time()
        
        thread = threading.Thread(target=self._mine_loop, daemon=True)
        thread.start()
    
    def _mine_loop(self):
        """Boucle de minage"""
        nonce = 0
        last_update = time.time()
        
        while self.is_mining:
            # Simuler le minage
            for _ in range(1000):
                nonce += 1
                self.stats.total_hashes += 1
                
                # Créer un hash
                data = f"VEIL_{nonce}_{time.time()}".encode()
                h = hashlib.sha256(data).hexdigest()
                
                # Vérifier si on a trouvé un bloc
                if h.startswith(self.target):
                    self.stats.blocks_mined += 1
                    self._found_block(nonce, h)
                    nonce = 0
            
            # Mettre à jour les stats
            if time.time() - last_update > 2:
                self._update_display()
                last_update = time.time()
    
    def _found_block(self, nonce, hash_val):
        """Appelé quand un bloc est trouvé"""
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}🎉 BLOC TROUVÉ !{RESET}")
        print(f"   Nonce: {nonce:,}")
        print(f"   Hash: {hash_val[:40]}...")
        print(f"   Récompense: +50 VEIL")
        print(f"{GREEN}{'='*60}{RESET}\n")
        
        # Envoyer au serveur
        try:
            requests.post(f"{self.api_url}/api/miner/start", json={"wallet": self.wallet_name})
            self.balance += 50
        except:
            pass
    
    def _update_display(self):
        """Afficher les stats en temps réel"""
        elapsed = time.time() - self.stats.start_time
        if elapsed > 0:
            self.stats.hashrate = self.stats.total_hashes / elapsed
        
        # Calculer ETA
        avg_needed = 16 ** self.difficulty
        if self.stats.hashrate > 0:
            eta_sec = max(0, (avg_needed - self.stats.total_hashes) / self.stats.hashrate)
            if eta_sec > 3600:
                eta = f"{eta_sec/3600:.1f}h"
            elif eta_sec > 60:
                eta = f"{eta_sec/60:.1f}min"
            else:
                eta = f"{eta_sec:.0f}s"
        else:
            eta = "..."
        
        # Barre de progression
        progress = min(100, (self.stats.total_hashes / avg_needed) * 100)
        bar_len = 30
        filled = int(bar_len * progress / 100)
        bar = f"{GREEN}{'█' * filled}{RESET}{'░' * (bar_len - filled)}"
        
        # Effacer la ligne précédente
        sys.stdout.write("\r\033[K")
        
        print(f"\r{WHITE}⛏️  {self.stats.hashrate:,.0f} H/s | {bar} {progress:.1f}% | "
              f"📦 {self.stats.blocks_mined} blocs | "
              f"⏳ ETA: {eta} | "
              f"💰 {self.balance:.2f} VEIL{RESET}", end="")
    
    def stop(self):
        """Arrêter le minage"""
        self.is_mining = False
        elapsed = time.time() - self.stats.start_time
        print(f"\n\n{RED}{'='*60}{RESET}")
        print(f"{RED}🛑 MINAGE ARRÊTÉ{RESET}")
        print(f"   ⏱️  Durée: {elapsed/60:.1f} minutes")
        print(f"   ⚡ Hashrate moyen: {self.stats.hashrate:,.0f} H/s")
        print(f"   📦 Blocs trouvés: {self.stats.blocks_mined}")
        print(f"   💰 Solde final: {self.balance:.2f} VEIL")
        print(f"{RED}{'='*60}{RESET}\n")

# ==================== MAIN ====================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    
    print(f"{CYAN}[*] Connexion au serveur {API_URL}...{RESET}")
    
    # Vérifier que le serveur répond
    try:
        res = requests.get(f"{API_URL}/api/stats", timeout=5)
        stats = res.json()
        print(f"{GREEN}[✓] Serveur connecté !{RESET}")
        print(f"    📊 Hauteur: {stats.get('height', 0)} blocs")
        print(f"    🎯 Difficulté: {stats.get('difficulty', 3)}")
        print(f"    💰 Récompense: {stats.get('current_reward', 50)} VEIL\n")
    except:
        print(f"{RED}[✗] Impossible de contacter le serveur{RESET}")
        print(f"{YELLOW}[!] Vérifie que le serveur est en ligne{RESET}\n")
        # Mode local
        print(f"{YELLOW}[!] Passage en mode local...{RESET}\n")
    
    # Login
    print(f"{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}🔐 CONNEXION WALLET{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    wallet_name = input(f"{WHITE}Nom du wallet: {RESET}").strip()
    if not wallet_name:
        wallet_name = "default"
    
    seed = input(f"{WHITE}Seed phrase (12 mots): {RESET}").strip()
    
    miner = VeilMiner(API_URL, wallet_name)
    
    if seed:
        if not miner.login(seed):
            print(f"{YELLOW}[!] Connexion échouée, passage en mode hors-ligne{RESET}")
    
    miner.difficulty = stats.get('difficulty', 3) if 'stats' in dir() else 3
    miner.target = "0" * miner.difficulty
    
    # Démarrer
    miner.start()
    
    print(f"\n{YELLOW}[!] Appuyez sur Ctrl+C pour arrêter{RESET}\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        miner.stop()

if __name__ == "__main__":
    main()
