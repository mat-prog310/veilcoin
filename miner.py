#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    ⛏️  VEILCOIN MINER  ⛏️                     ║
║                    Terminal v1.0.0                           ║
║              Mine Simply. Transact Privately.                ║
╚══════════════════════════════════════════════════════════════╝
"""
import hashlib
import time
import os
import sys
import json
import urllib.request
import ssl

# ==================== CONFIGURATION ====================

API_URL = "https://veilcoin-fvzp.onrender.com"

# Couleurs Windows
if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    GREEN = ""
    YELLOW = ""
    RED = ""
    CYAN = ""
    WHITE = ""
    RESET = ""
else:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

# ==================== MINER ====================

class VeilMiner:
    def __init__(self):
        self.wallet_name = ""
        self.wallet_seed = ""
        self.is_mining = False
        self.hashrate = 0.0
        self.total_hashes = 0
        self.blocks_mined = 0
        self.start_time = 0
        self.difficulty = 4
        self.balance = 0.0
        self.connected = False

    def api_call(self, endpoint, data=None):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            if data:
                req = urllib.request.Request(
                    f"{API_URL}{endpoint}",
                    data=json.dumps(data).encode(),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
            else:
                req = urllib.request.Request(f"{API_URL}{endpoint}")
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            return None

    def login(self, name, seed):
        self.wallet_name = name
        self.wallet_seed = seed
        
        result = self.api_call("/api/wallet/login", {
            "name": name,
            "seed_phrase": seed
        })
        
        if result and result.get("success"):
            self.balance = result.get("balance", 0)
            self.connected = True
            return True
        return False

    def get_stats(self):
        result = self.api_call("/api/stats")
        if result:
            self.difficulty = result.get("difficulty", 4)
        return result

    def mine(self):
        self.get_stats()
        target = "0" * self.difficulty
        self.is_mining = True
        self.start_time = time.time()
        self.total_hashes = 0
        self.blocks_mined = 0
        nonce = 0
        
        print(f"\n{'-'*60}")
        print(f"🔒 DÉMARRAGE DU MINAGE")
        print(f"{'-'*60}")
        print(f"  🎯 Cible: {target}...")
        print(f"  📊 Difficulté: {self.difficulty}")
        print(f"  💰 Récompense: 50 VEIL/bloc")
        print(f"{'-'*60}\n")
        
        last_print = time.time()
        last_balance_check = time.time()
        
        while self.is_mining:
            for _ in range(500):
                nonce += 1
                self.total_hashes += 1
                
                data = f"VEIL_{nonce}_{time.time()}".encode()
                h = hashlib.sha256(data).hexdigest()
                
                if h.startswith(target):
                    self.blocks_mined += 1
                    elapsed = time.time() - self.start_time
                    print(f"\n{'='*60}")
                    print(f"🎉 BLOC TROUVÉ !")
                    print(f"   Nonce: {nonce:,}")
                    print(f"   Temps: {elapsed:.1f}s")
                    print(f"   Hash: {h[:40]}...")
                    print(f"{'='*60}\n")
                    
                    # Créditer le wallet
                    self.api_call("/api/miner/start", {"wallet": self.wallet_name})
                    self.balance += 50
                    nonce = 0
            
            if time.time() - last_print > 2:
                elapsed = time.time() - self.start_time
                if elapsed > 0:
                    self.hashrate = self.total_hashes / elapsed
                
                avg_needed = 16 ** self.difficulty
                if self.hashrate > 0:
                    eta_sec = max(0, (avg_needed - self.total_hashes) / self.hashrate)
                    eta = f"{eta_sec/60:.1f}min" if eta_sec > 60 else f"{eta_sec:.0f}s"
                else:
                    eta = "..."
                
                progress = min(100, (self.total_hashes / avg_needed) * 100)
                bar_len = 30
                filled = int(bar_len * progress / 100)
                bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
                
                sys.stdout.write(f"\r⛏️  {self.hashrate:,.0f} H/s | [{bar}] {progress:.1f}% | 📦 {self.blocks_mined} | ⏳ {eta} | 💰 {self.balance:.1f} VEIL  ")
                sys.stdout.flush()
                
                last_print = time.time()
            
            # Vérifier le solde toutes les 30 secondes
            if time.time() - last_balance_check > 30 and self.connected:
                result = self.api_call(f"/api/wallet/{self.wallet_name}/balance")
                if result:
                    self.balance = result.get("balance_veil", self.balance)
                last_balance_check = time.time()

    def stop(self):
        self.is_mining = False
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0
        
        print(f"\n\n{'='*60}")
        print(f"🛑 MINAGE ARRÊTÉ")
        print(f"{'='*60}")
        print(f"  ⏱️  Durée: {elapsed/60:.1f} min")
        print(f"  ⚡ Hashrate: {self.hashrate:,.0f} H/s")
        print(f"  📦 Blocs: {self.blocks_mined}")
        print(f"  💰 Solde: {self.balance:.2f} VEIL")
        print(f"{'='*60}\n")

# ==================== MAIN ====================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██╗   ██╗███████╗██╗██╗      ██████╗ ██████╗ ██╗███╗   ██╗
║   ██║   ██║██╔════╝██║██║     ██╔════╝██╔═══██╗██║████╗  ██║
║   ██║   ██║█████╗  ██║██║     ██║     ██║   ██║██║██╔██╗ ██║
║   ╚██╗ ██╔╝██╔══╝  ██║██║     ██║     ██║   ██║██║██║╚██╗██║
║    ╚████╔╝ ███████╗██║███████╗╚██████╗╚██████╔╝██║██║ ╚████║
║     ╚═══╝  ╚══════╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝
║                                                              ║
║                  ⛏️  MINER TERMINAL v1.0  ⛏️                   ║
║                  Mine Simply. Transact Privately.            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    miner = VeilMiner()
    
    print(f"Connexion au réseau...")
    stats = miner.get_stats()
    if stats:
        print(f"[OK] Réseau connecté !")
        print(f"     Hauteur: {stats.get('height', 0)} blocs")
        print(f"     Difficulté: {stats.get('difficulty', 4)}")
    else:
        print(f"[!] Mode hors-ligne")
    
    print(f"\n{'='*60}")
    print(f"CONNEXION WALLET")
    print(f"{'='*60}")
    
    name = input(f"Nom du wallet: ").strip()
    if not name:
        name = "default"
    
    seed = input(f"Seed phrase (12 mots): ").strip()
    
    if seed:
        if miner.login(name, seed):
            print(f"[OK] Connecté ! Solde: {miner.balance:.4f} VEIL")
        else:
            print(f"[!] Connexion échouée, mode hors-ligne")
    
    miner.mine()
    
    print(f"\nAppuyez sur Ctrl+C pour arrêter...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        miner.stop()
        print("Appuyez sur Entrée pour quitter...")
        input()

if __name__ == "__main__":
    main()
