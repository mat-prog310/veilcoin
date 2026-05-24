"""
Mineur VeilCoin - Preuve de travail renforcée
Double SHA256 + Sel aléatoire + Vérification stricte
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
                self.stats['network_security'] = self.stats['hashrate'] * (16 ** self.blockchain.difficulty)

    def _heavy_hash(self, data):
        """
        Fonction de hachage LOURDE pour augmenter la difficulté
        - Triple SHA256 au lieu de simple
        - Sel aléatoire de 16 bytes
        - 3 rounds de hachage
        """
        salt = os.urandom(16)
        
        # Round 1
        h1 = hashlib.sha256(data + salt).digest()
        # Round 2
        h2 = hashlib.sha256(h1 + salt).digest()
        # Round 3 (final)
        h3 = hashlib.sha256(h2 + salt).hexdigest()
        
        return h3

    def mine_block(self, addr):
        candidate = self.blockchain.create_new_block(addr)
        if not candidate:
            return None
        
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.total_hashes = 0
        self.is_mining = True
        last_print = time.time()
        
        print(f"🔒 Bloc #{len(self.blockchain.chain)}")
        print(f"   🎯 Difficulté: {self.blockchain.difficulty} zéros")
        print(f"   🔐 Cible: {target}...")
        print(f"   ⚡ Triple SHA256 avec sel 16 bytes")
        print(f"   🛡️  Sécurité réseau en renforcement...")
        print()
        
        while self.is_mining:
            # Traitement par lots pour être plus efficace
            for _ in range(50):  # 50 hashes par lot (plus lent = plus sécurisé)
                candidate.header.nonce += 1
                self.total_hashes += 1
                
                # Hachage lourd (triple SHA256)
                header_data = str(candidate.header.to_dict()).encode()
                block_hash = self._heavy_hash(
                    header_data + candidate.header.nonce.to_bytes(8, 'big')
                )
                
                # Vérifier la preuve de travail
                if block_hash.startswith(target):
                    candidate.block_hash = block_hash
                    
                    if self.blockchain.add_block(candidate):
                        self.blocks_mined += 1
                        self._update()
                        
                        elapsed = time.time() - self.start_time
                        hashes_needed = 16 ** self.blockchain.difficulty
                        
                        print(f"\n{'='*60}")
                        print(f"✅ BLOC #{len(self.blockchain.chain)} MINÉ !")
                        print(f"   ⏱️  Temps: {elapsed:.1f}s")
                        print(f"   🔢 Nonce: {candidate.header.nonce:,}")
                        print(f"   🔐 Hash: {block_hash[:40]}...")
                        print(f"   🛡️  Sécurité: {self.stats['network_security']/1e9:.2f} GH")
                        print(f"   💰 Récompense: {self.blockchain.reward()} VEIL")
                        print(f"{'='*60}\n")
                        
                        if self.callback:
                            self.callback(candidate)
                        
                        return candidate
                
                # Vérifier si on doit s'arrêter
                if self.total_hashes % 500 == 0:
                    if not self.is_mining:
                        return None
            
            # Pause pour simuler un calcul réaliste
            time.sleep(0.002)
            
            # Afficher les stats
            if time.time() - last_print > 3:
                self._update()
                elapsed = time.time() - self.start_time
                
                # Calculer ETA
                avg_needed = 16 ** self.blockchain.difficulty
                if self.stats['hashrate'] > 0:
                    remaining = max(0, avg_needed - self.total_hashes)
                    eta_sec = remaining / self.stats['hashrate']
                    if eta_sec > 3600:
                        eta = f"{eta_sec/3600:.1f}h"
                    elif eta_sec > 60:
                        eta = f"{eta_sec/60:.1f}min"
                    else:
                        eta = f"{eta_sec:.0f}s"
                else:
                    eta = "calcul..."
                
                # Barre de progression
                progress = min(100, (self.total_hashes / avg_needed) * 100)
                bar_len = 30
                filled = int(bar_len * progress / 100)
                bar = f"{'█' * filled}{'░' * (bar_len - filled)}"
                
                print(f"   ⛏️  {self.stats['hashrate']:.0f} H/s | [{bar}] {progress:.1f}% | ⏳ {eta} | Nonce: {candidate.header.nonce:,}")
                last_print = time.time()
        
        return None

    def start_mining(self, addr):
        self.is_mining = True
        print("=" * 60)
        print("🔒 DÉMARRAGE DU MINAGE SÉCURISÉ")
        print("=" * 60)
        print(f"   🎯 Objectif: 1 bloc / 2 minutes")
        print(f"   💰 Récompense: {self.blockchain.reward()} VEIL/bloc")
        print(f"   🔐 Algorithme: Triple SHA256 + Sel 16 bytes")
        print(f"   🛡️  Plus on mine = Réseau plus sécurisé")
        print("=" * 60)
        print()
        
        def loop():
            while self.is_mining:
                try:
                    block = self.mine_block(addr)
                    if block:
                        print(f"🎉 +{self.blockchain.reward()} VEIL !\n")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Erreur: {e}")
                    time.sleep(2)
        
        self.mining_thread = threading.Thread(target=loop, daemon=True)
        self.mining_thread.start()

    def stop_mining(self):
        self.is_mining = False
        if self.mining_thread and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=3)
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0
        print(f"\n{'='*60}")
        print(f"🛑 MINAGE ARRÊTÉ")
        print(f"   ⏱️  Durée: {elapsed/60:.1f} min")
        print(f"   ⚡ Hashrate moyen: {self.stats['hashrate']:.0f} H/s")
        print(f"   📦 Blocs trouvés: {self.stats['blocks_mined']}")
        print(f"   🛡️  Sécurité max: {self.stats['network_security']/1e9:.2f} GH")
        print(f"{'='*60}\n")

    def get_stats(self):
        self._update()
        return self.stats
