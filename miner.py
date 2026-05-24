#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    ⛏️  VEILCOIN MINER  ⛏️                     ║
║                    Terminal v2.0.0                           ║
║              Mine Simply. Transact Privately.                ║
║              Difficulté: 6 zéros - EXTRÊME                  ║
╚══════════════════════════════════════════════════════════════╝
"""
import hashlib
import time
import os
import sys
import json
import urllib.request
import ssl

API_URL = "https://veilcoin.xyz"

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
        self.diff = 6
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
        except:
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
        if r: self.diff = r.get("difficulty", 6)
        return r

    def hh(self, data):
        s = os.urandom(64)
        h = data + s
        for _ in range(5): h = hashlib.sha256(h).digest()
        return h.hex()

    def mine(self):
        self.stats()
        tgt = "0" * self.diff
        self.mining = True
        self.t0 = time.time()
        self.hashes = 0
        self.blocks = 0
        nonce = 0
        lp = time.time()

        print(f"\n{G}{'='*60}{X}")
        print(f"{G}🔒 MINAGE LANCÉ{X}")
        print(f"{G}{'='*60}{X}")
        print(f"  🎯 Difficulté: {Y}{self.diff}{X} zéros (EXTRÊME)")
        print(f"  💰 Récompense: {G}25{X} VEIL/bloc")
        print(f"  ⏱️  Temps estimé: {Y}2-10 heures{X} par bloc")
        print(f"{G}{'='*60}{X}\n")

        while self.mining:
            for _ in range(5):
                nonce += 1
                self.hashes += 1
                h = self.hh(f"VEIL_{nonce}_{time.time()}".encode())
                if h.startswith(tgt):
                    self.blocks += 1
                    e = time.time() - self.t0
                    print(f"\n{G}{'='*60}{X}")
                    print(f"{G}🎉 BLOC TROUVÉ !{X}")
                    print(f"   ⏱️  Temps: {e/3600:.1f}h")
                    print(f"   💰 +25 VEIL")
                    print(f"{G}{'='*60}{X}\n")
                    self.api("/api/miner/start", {"wallet": self.wallet})
                    self.bal += 25
                    nonce = 0
            time.sleep(0.01)
            if time.time() - lp > 10:
                e = time.time() - self.t0
                if e > 0: self.hr = self.hashes / e
                avg = 16 ** self.diff
                eta = "..."
                if self.hr > 0:
                    es = max(0, avg - self.hashes) / self.hr
                    eta = f"{es/3600:.1f}h" if es > 3600 else f"{es/60:.1f}min" if es > 60 else f"{es:.0f}s"
                pct = min(100, (self.hashes / avg) * 100)
                bar = "█" * int(pct/2) + "░" * (50 - int(pct/2))
                sys.stdout.write(f"\r{G}⛏️{X} {self.hr:.0f} H/s | {bar} {pct:.4f}% | ⏳{eta} | 💰{self.bal:.1f} VEIL  ")
                sys.stdout.flush()
                lp = time.time()

    def stop(self):
        self.mining = False
        e = time.time() - self.t0 if self.t0 > 0 else 0
        print(f"\n\n{R}{'='*60}{X}")
        print(f"{R}🛑 MINAGE ARRÊTÉ{X}")
        print(f"   ⏱️  Durée: {e/3600:.1f}h")
        print(f"   ⚡ Hashrate: {self.hr:.0f} H/s")
        print(f"   📦 Blocs: {self.blocks}")
        print(f"   💰 Solde: {self.bal:.1f} VEIL")
        print(f"{R}{'='*60}{X}\n")

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
║                  ⛏️  MINER v2.0 - DIFF 6  ⛏️                  ║
╚══════════════════════════════════════════════════════════════╝{X}""")

    m = VeilMiner()
    print(f"{C}Connexion à {API_URL}...{X}")
    s = m.stats()
    if s:
        print(f"{G}[OK]{X} Hauteur: {s.get('height',0)} | Difficulté: {s.get('difficulty',6)}")
    
    print(f"\n{G}{'='*60}{X}")
    print(f"{G}CONNEXION WALLET{X}")
    print(f"{G}{'='*60}{X}")
    name = input(f"{W}Nom du wallet: {X}").strip() or "default"
    seed = input(f"{W}Seed phrase (12 mots): {X}").strip()
    if seed and m.login(name, seed):
        print(f"{G}[OK]{X} Connecté ! Solde: {m.bal:.4f} VEIL")
    
    m.mine()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        m.stop()
        input(f"{W}Entrée pour quitter...{X}")

if __name__ == "__main__":
    main()
