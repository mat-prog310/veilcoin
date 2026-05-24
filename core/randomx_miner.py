"""
Mineur VeilCoin - Sécurité réseau par Proof of Work
Chaque hash calculé renforce la sécurité de la blockchain
"""
import hashlib
import time
import threading
import os

class RandomXMiner:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.is_mining = False
        self.hashrate = 0.0
        self.total_hashes = 0
        self.start_time = 0
        self.blocks_mined = 0
        self.mining_thread = None
        self.callback = None
        self.network_security = 0  # Niveau de sécurité du réseau
        self.stats = {
            'hashrate': 0,
            'total_hashes': 0,
            'blocks_mined': 0,
            'current_difficulty': blockchain.difficulty,
            'accepted_shares': 0,
            'network_security': 0
        }

    def set_callback(self, cb):
        self.callback = cb

    def _update(self):
        if self.start_time > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.stats['hashrate'] = self.total_hashes / elapsed
                self.stats['total_hashes'] = self.total_hashes
                self.stats['blocks_mined'] = self.blocks_mined
                self.stats['current_difficulty'] = self.blockchain.difficulty
                # Sécurité = hashrate × difficulté
                self.stats['network_security'] = self.stats['hashrate'] * (16 ** self.blockchain.difficulty)

    def _secure_hash(self, data):
        """
        Fonction de hachage sécurisée
        Utilise SHA256 + sel aléatoire pour renforcer la sécurité
        """
        # Ajouter un sel aléatoire pour rendre plus difficile à prédire
        salt = os.urandom(8)
        # Double SHA256 comme Bitcoin
        h1 = hashlib.sha256(data + salt).digest()
        h2 = hashlib.sha256(h1).digest()
        return h2.hex()

    def mine_block(self, addr):
        candidate = self.blockchain.create_new_block(addr)
        if not candidate:
            return None
        
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.total_hashes = 0
        self.is_mining = True
        last_print = time.time()
        
        print(f"🔒 Bloc #{len(self.blockchain.chain)} | Difficulté: {self.blockchain.difficulty}")
        print(f"   🎯 Cible: {target}...")
        print(f"   🛡️  Sécurité réseau en renforcement...")
        
        while self.is_mining:
            # Calcul plus lourd = plus sécurisé
            for _ in range(100):
                candidate.header.nonce += 1
                self.total_hashes += 1
                
                # Hachage sécurisé avec sel
                header_data = str(candidate.header.to_dict()).encode()
                block_hash = self._secure_hash(
                    header_data + candidate.header.nonce.to_bytes(8, 'big')
                )
                
                # Vérifier la preuve de travail
                if block_hash.startswith(target):
                    candidate.block_hash = block_hash
                    
                    if self.blockchain.add_block(candidate):
                        self.blocks_mined += 1
                        self._update()
                        
                        elapsed = time.time() - self.start_time
                        print(f"✅ BLOC #{len(self.blockchain.chain)} MINÉ !")
                        print(f"   ⏱️  {elapsed:.1f}s | 🛡️  Sécurité: {self.stats['network_security']:.0f}")
                        
                        if self.callback:
                            self.callback(candidate)
                        
                        return candidate
                
                if self.total_hashes % 1000 == 0:
                    if not self.is_mining:
                        return None
            
            time.sleep(0.001)
            
            if time.time() - last_print > 3:
                self._update()
                elapsed = time.time() - self.start_time
                
                # Calculer ETA
                eta = "Calcul..."
                if self.stats['hashrate'] > 0:
                    avg_needed = 16 ** self.blockchain.difficulty
                    eta_sec = max(0, (avg_needed - self.total_hashes) / self.stats['hashrate'])
                    if eta_sec > 3600:
                        eta = f"{eta_sec/3600:.1f}h"
                    elif eta_sec > 60:
                        eta = f"{eta_sec/60:.1f}min"
                    else:
                        eta = f"{eta_sec:.0f}s"
                
                print(f"   ⛏️  {self.stats['hashrate']:.0f} H/s | 🛡️  Sécu: {self.stats['network_security']/1e6:.1f}M | ⏳ ETA: {eta}")
                last_print = time.time()
        
        return None

    def start_mining(self, addr):
        self.is_mining = True
        print("🔒 Démarrage du minage sécurisé")
        print(f"   🎯 Objectif: 1 bloc / 2 minutes")
        print(f"   💰 Récompense: {self.blockchain.reward()} VEIL/bloc")
        print(f"   🛡️  Plus on mine = Plus le réseau est sécurisé")
        print()
        
        def loop():
            while self.is_mining:
                try:
                    block = self.mine_block(addr)
                    if block:
                        print(f"🎉 +{self.blockchain.reward()} VEIL !")
                        print(f"🛡️  Réseau renforcé !\n")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️ Erreur: {e}")
                    time.sleep(2)
        
        self.mining_thread = threading.Thread(target=loop, daemon=True)
        self.mining_thread.start()

    def stop_mining(self):
        self.is_mining = False
        if self.mining_thread and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=3)
        print("🛑 Minage arrêté")

    def get_stats(self):
        self._update()
        return self.stats
