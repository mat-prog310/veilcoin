#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║                    ⛏️  VEILCOIN MINER  ⛏️                     ║
║                    Terminal v3.0.0                           ║
║              Mine Securely. Transact Privately.              ║
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
import random
import uuid

API_URL = "https://veilcoin.xyz"

# Générer un fingerprint unique pour cet appareil
def get_device_fingerprint():
    """Génère un fingerprint unique basé sur l'appareil"""
    try:
        import platform
        fingerprint_data = [
            platform.node(),
            platform.processor(),
            platform.machine(),
            str(uuid.getnode()),  # MAC address
            os.name,
            sys.version[:20]
        ]
        fingerprint_str = "|".join(fingerprint_data)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    except:
        # Fallback
        return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()

DEVICE_FINGERPRINT = get_device_fingerprint()

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
        self.diff = 5
        self.bal = 0.0
        self.last_block_time = 0
        self.hash_rate_limit = 800

    def api(self, ep, data=None, method='POST'):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            headers = {
                'Content-Type': 'application/json',
                'X-Device-Fingerprint': DEVICE_FINGERPRINT
            }
            
            if method == 'POST' and data:
                req = urllib.request.Request(f"{API_URL}{ep}",
                    data=json.dumps(data).encode(),
                    headers=headers, method='POST')
            else:
                req = urllib.request.Request(f"{API_URL}{ep}",
                    headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                error_data = json.loads(e.read().decode())
                return error_data
            except:
                return {'success': False, 'error': f'HTTP {e.code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def login(self, name, seed):
        self.wallet = name
        r = self.api("/api/wallet/login", {"name": name, "seed_phrase": seed})
        if r and r.get("success"):
            self.bal = r.get("balance", 0)
            return True
        return False

    def stats(self):
        r = self.api("/api/stats", method='GET')
        if r: 
            self.diff = r.get("difficulty", 5)
        return r

    def get_mempool(self):
        try:
            r = self.api("/api/miner/mempool", method='GET')
            if r:
                return r.get('transactions', [])
        except:
            pass
        return []

    def get_last_block(self):
        try:
            r = self.api("/api/blockchain/blocks", method='GET')
            if r and r.get('blocks'):
                blocks = r.get('blocks', [])
                if blocks:
                    return blocks[-1]
        except:
            pass
        return None
    
    def get_farm_status(self):
        """Vérifie le statut anti-ferme"""
        if not self.wallet:
            return None
        return self.api(f"/api/miner/farm_status?wallet={self.wallet}", method='GET')

    def submit_block(self, nonce, hash_proof, transactions, previous_hash):
        submit_data = {
            "wallet": self.wallet,
            "nonce": nonce,
            "hash": hash_proof,
            "transactions": transactions,
            "previous_hash": previous_hash,
            "difficulty": self.diff
        }
        return self.api("/api/miner/submit_block", submit_data, method='POST')

    def slow_hash(self, data):
        time.sleep(0.001)
        return hashlib.sha256(data.encode()).hexdigest()

    def mine(self):
        self.stats()
        tgt = "0" * self.diff
        self.mining = True
        self.t0 = time.time()
        self.hashes = 0
        self.blocks = 0
        nonce = random.randint(0, 1000000)
        lp = time.time()
        
        last_hash_time = time.time()
        hash_count_this_second = 0
        last_mempool_fetch = 0
        mempool = []
        previous_hash = "0" * 64

        print(f"\n{G}{'='*60}{X}")
        print(f"{G}🔒 MINAGE LANCÉ - VERSION SÉCURISÉE{X}")
        print(f"{G}{'='*60}{X}")
        print(f"  🎯 Difficulté: {Y}{self.diff}{X} zéros")
        print(f"  💰 Récompense: {G}50{X} VEIL/bloc")
        print(f"  🐌 Limite hashrate: {Y}{self.hash_rate_limit}{X} H/s")
        print(f"  🔒 Limite anti-ferme: {Y}3 blocs/heure maximum{X}")
        print(f"  🔑 Fingerprint: {Y}{DEVICE_FINGERPRINT[:16]}...{X}")
        print(f"{G}{'='*60}{X}\n")

        # Vérifier le statut anti-ferme au début
        farm_status = self.get_farm_status()
        if farm_status:
            blocks_left = farm_status.get('blocks_left_this_hour', 3)
            cooldown = farm_status.get('cooldown_minutes', 0)
            if cooldown > 0:
                print(f"{R}⚠️ Cooldown actif: {cooldown} minutes restantes{X}\n")
            else:
                print(f"{G}✅ {blocks_left} blocs disponibles cette heure{X}\n")

        while self.mining:
            # Vérifier le statut anti-ferme périodiquement
            if time.time() - last_mempool_fetch > 30:
                farm_status = self.get_farm_status()
                if farm_status and not farm_status.get('can_mine', True):
                    print(f"\n{R}⛔ Limite atteinte ou cooldown actif !{X}")
                    print(f"   Blocs minés: {farm_status.get('blocks_mined_this_hour', 0)}/3")
                    print(f"   Attendez {farm_status.get('cooldown_minutes', 0)} minutes{X}\n")
                    time.sleep(60)
                    continue
                last_mempool_fetch = time.time()
            
            # Récupérer la mempool
            if time.time() - last_mempool_fetch > 10:
                mempool = self.get_mempool()
                last_block = self.get_last_block()
                if last_block:
                    previous_hash = last_block.get('hash', "0" * 64)
            
            hash_count_this_second += 1
            if hash_count_this_second >= self.hash_rate_limit:
                elapsed = time.time() - last_hash_time
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                hash_count_this_second = 0
                last_hash_time = time.time()
            
            nonce += 1
            self.hashes += 1
            
            block_data = {
                'miner': self.wallet,
                'nonce': nonce,
                'transactions': mempool[:10],
                'previous_hash': previous_hash,
                'timestamp': time.time()
            }
            
            block_string = json.dumps(block_data, sort_keys=True)
            h = self.slow_hash(block_string)
            
            if h.startswith(tgt):
                self.blocks += 1
                e = time.time() - self.t0
                
                print(f"\n{G}{'='*60}{X}")
                print(f"{G}🎉 BLOC TROUVÉ !{X}")
                print(f"   ⏱️  Temps: {e/60:.1f}min ({e:.0f}s)")
                print(f"   🔑 Nonce: {nonce}")
                print(f"   🔗 Hash: {h[:20]}...")
                print(f"   📦 Transactions: {len(mempool[:10])}")
                print(f"   💰 Récompense: +50 VEIL")
                print(f"{G}{'='*60}{X}")
                
                result = self.submit_block(nonce, h, mempool[:10], previous_hash)
                
                if result and result.get("success"):
                    self.bal = result.get("new_balance", self.bal + 50)
                    blocks_left = result.get('blocks_left_this_hour', 3)
                    print(f"   ✅ Bloc validé !")
                    print(f"   💰 Nouveau solde: {self.bal:.4f} VEIL")
                    print(f"   📊 Block #: {result.get('block_index')}")
                    print(f"   ⏱️  Plus que {blocks_left} blocs cette heure")
                else:
                    error = result.get('error', 'unknown') if result else 'API error'
                    print(f"   ❌ Bloc refusé: {error}")
                
                nonce = random.randint(0, 1000000)
                last_mempool_fetch = 0
            
            if time.time() - lp > 5:
                e = time.time() - self.t0
                if e > 0: 
                    self.hr = self.hashes / e
                
                avg = 16 ** self.diff
                
                if self.hashes < avg:
                    if self.hr > 0:
                        es = max(0, avg - self.hashes) / self.hr
                        if es > 3600:
                            eta = f"{es/3600:.1f}h"
                        elif es > 60:
                            eta = f"{es/60:.1f}min"
                        else:
                            eta = f"{es:.0f}s"
                    
                    pct = (self.hashes / avg) * 100
                    bar_len = int(pct / 2)
                    bar = "█" * bar_len + "░" * (50 - bar_len)
                    sys.stdout.write(f"\r{G}⛏️{X} {self.hr:.0f} H/s | {bar} {pct:.1f}% | ⏳{eta} | 💰{self.bal:.1f} VEIL | 🎯{self.blocks} blocs  ")
                else:
                    sys.stdout.write(f"\r{G}⛏️{X} {self.hr:.0f} H/s | 🔍 Recherche... | 💰{self.bal:.1f} VEIL | 🎯{self.blocks} blocs  ")
                
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
║            ⛏️  MINER v3.0 - SÉCURISÉ  ⛏️                    ║
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
        print(f"{C}🔑 Fingerprint: {DEVICE_FINGERPRINT[:32]}...{X}")
    else:
        print(f"{R}❌ Échec de connexion{X}")
        return
    
    try:
        m.mine()
    except KeyboardInterrupt:
        m.stop()
        input(f"{W}Entrée pour quitter...{X}")

if __name__ == "__main__":
    main()