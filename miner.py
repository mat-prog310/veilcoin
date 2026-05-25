#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    ⛏️  VEILCOIN MINER  ⛏️                     ║
║                    Terminal v2.0.0                           ║
║              Mine Simply. Transact Privately.                ║
║              Difficulté: 5 zéros (EXTREME)                   ║
╚══════════════════════════════════════════════════════════════╝
"""
import hashlib
import time
import os
import sys
import json
import urllib.request
import urllib.error
import ssl

# ⚠️ CORRECTION: URL de votre serveur Render
API_URL = "https://veilcoin-fvzp.onrender.com"

if os.name == 'nt':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    G = Y = R = C = W = X = ""
else:
    G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"
    C = "\033[96m"; W = "\033[97m"; X = "\033[0m"

class VeilMiner:
    def __init__(self):
        self.wallet = ""
        self.mining = False
        self.hr = 0.0
        self.hashes = 0
        self.blocks = 0
        self.t0 = 0
        self.diff = 5  # 🔒 DIFFICULTÉ 5 FIXE (EXTREME)
        self.bal = 0.0

    def api(self, ep, data=None):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            if data:
                req = urllib.request.Request(f"{API_URL}{ep}",
                    data=json.dumps(data).encode(),
                    headers={'Content-Type': 'application/json'}, method='POST')
            else:
                req = urllib.request.Request(f"{API_URL}{ep}")
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                return json.loads(r.read().decode())
        except urllib.error.URLError as e:
            print(f"{R}❌ Erreur réseau: {e.reason}{X}")
            return None
        except Exception as e:
            print(f"{R}❌ Erreur: {e}{X}")
            return None

    def login(self, name, seed):
        self.wallet = name
        r = self.api("/api/wallet/login", {"name": name, "seed_phrase": seed})
        if r and r.get("success"):
            self.bal = r.get("balance", 0)
            return True
        return False

    def stats(self):
        r = self.api("/api/stats")
        if r: 
            server_diff = r.get("difficulty", 5)
            if server_diff != self.diff:
                print(f"{Y}⚠️ Note: Difficulté serveur = {server_diff}, locale = {self.diff}{X}")
        return r

    def mine(self):
        self.stats()
        tgt = "0" * self.diff  # "00000"
        self.mining = True
        self.t0 = time.time()
        self.hashes = 0
        self.blocks = 0
        nonce = 0
        lp = time.time()
        
        # ⚠️ CORRECTION: Base fixe sans time.time() dans le hash
        base = f"VEIL_{self.wallet}_{int(self.t0)}"

        print(f"\n{G}{'='*60}{X}")
        print(f"{G}🔒 MINAGE LANCÉ - DIFFICULTÉ EXTREME{X}")
        print(f"{G}{'='*60}{X}")
        print(f"  🎯 Difficulté: {Y}{self.diff}{X} zéros (EXTREME)")
        print(f"  💰 Récompense: {G}25{X} VEIL/bloc")
        print(f"  🔢 Base: {Y}{base}{X}")
        print(f"  ⚡ Hashes nécessaires: ~{16**self.diff:,}")
        print(f"{G}{'='*60}{X}\n")

        while self.mining:
            for _ in range(1000):
                nonce += 1
                self.hashes += 1
                
                # ⚠️ CORRECTION: time.time() enlevé, nonce est la seule variable
                h = hashlib.sha256(f"{base}_{nonce}".encode()).hexdigest()
                
                if h.startswith(tgt):
                    self.blocks += 1
                    e = time.time() - self.t0
                    print(f"\n{G}{'='*60}{X}")
                    print(f"{G}🎉 BLOC TROUVÉ !{X}")
                    print(f"   ⏱️  Temps: {e/60:.1f}min ({e:.0f}s)")
                    print(f"   🔑 Nonce: {nonce}")
                    print(f"   🔗 Hash: {h[:20]}...")
                    print(f"   💰 +25 VEIL")
                    print(f"{G}{'='*60}{X}")
                    
                    # ⚠️ CORRECTION: Soumission au serveur
                    submit_data = {
                        "wallet": self.wallet,
                        "nonce": nonce,
                        "hash": h,
                        "base": base,
                        "difficulty": self.diff
                    }
                    
                    result = self.api("/api/miner/submit_block", submit_data)
                    
                    if result and result.get("success"):
                        print(f"   ✅ Bloc validé sur le réseau !")
                        self.bal += 25
                        print(f"   💰 Nouveau solde: {self.bal:.4f} VEIL")
                    else:
                        error = result.get('error', 'unknown') if result else 'API error'
                        print(f"   ❌ Bloc refusé: {error}")
                    
                    # Reset pour le prochain bloc
                    nonce = 0
                    base = f"VEIL_{self.wallet}_{int(time.time())}"
            
            if time.time() - lp > 5:
                e = time.time() - self.t0
                if e > 0: 
                    self.hr = self.hashes / e
                avg = 16 ** self.diff
                eta = "..."
                if self.hr > 0:
                    es = max(0, avg - self.hashes) / self.hr
                    if es > 3600:
                        eta = f"{es/3600:.1f}h"
                    elif es > 60:
                        eta = f"{es/60:.1f}min"
                    else:
                        eta = f"{es:.0f}s"
                pct = min(100, (self.hashes / avg) * 100)
                bar = "█" * int(pct/2) + "░" * (50 - int(pct/2))
                sys.stdout.write(f"\r{G}⛏️{X} {self.hr:.0f} H/s | {bar} {pct:.2f}% | ⏳{eta} | 💰{self.bal:.1f} VEIL  ")
                sys.stdout.flush()
                lp = time.time()

    def stop(self):
        self.mining = False
        e = time.time() - self.t0 if self.t0 > 0 else 0
        print(f"\n\n{R}🛑 MINAGE ARRÊTÉ - {e/60:.1f} min | {self.blocks} blocs | {self.bal:.1f} VEIL{X}\n")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"""{G}
╔══════════════════════════════════════════════════════════════╗
║   ██╗   ██╗███████╗██╗██╗      ██████╗ ██████╗ ██╗███╗   ██╗
║   ██║   ██║██╔════╝██║██║     ██╔════╝██╔═══██╗██║████╗  ██║
║   ██║   ██║█████╗  ██║██║     ██║     ██║   ██║██║██╔██╗ ██║
║   ╚██╗ ██╔╝██╔══╝  ██║██║     ██║     ██║   ██║██║██║╚██╗██║
║    ╚████╔╝ ███████╗██║███████╗╚██████╗╚██████╔╝██║██║ ╚████║
║     ╚═══╝  ╚══════╝╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝
║            ⛏️  MINER v2.0 - DIFFICULTÉ 5 EXTREME  ⛏️          ║
╚══════════════════════════════════════════════════════════════╝{X}""")

    m = VeilMiner()
    print(f"{C}🌐 Connexion à {API_URL}...{X}")
    s = m.stats()
    if s:
        print(f"{G}[OK]{X} Hauteur: {s.get('height',0)} | Difficulté: {s.get('difficulty',5)}")
    
    print(f"\n{G}🔐 CONNEXION WALLET{X}")
    name = input(f"{W}Nom du wallet: {X}").strip() or "default"
    seed = input(f"{W}Seed phrase (12 mots): {X}").strip()
    if seed and m.login(name, seed):
        print(f"{G}[OK]{X} Connecté ! Solde: {m.bal:.4f} VEIL")
    
    try:
        m.mine()
    except KeyboardInterrupt:
        m.stop()
        input(f"{W}Entrée pour quitter...{X}")

if __name__ == "__main__":
    main()
