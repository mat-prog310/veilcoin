import hashlib
import time
import threading

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
            'accepted_shares': 0
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

    def mine_block(self, addr):
        candidate = self.blockchain.create_new_block(addr)
        if not candidate:
            return None
        
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.total_hashes = 0
        self.is_mining = True
        last_print = time.time()
        
        print(f"⛏️  Bloc #{len(self.blockchain.chain)} | Difficulté: {self.blockchain.difficulty} | Cible: {target}...")
        
        while self.is_mining:
            candidate.header.nonce += 1
            self.total_hashes += 1
            
            header_data = str(candidate.header.to_dict()).encode()
            block_hash = hashlib.sha256(
                header_data + candidate.header.nonce.to_bytes(8, 'big')
            ).hexdigest()
            
            if block_hash.startswith(target):
                candidate.block_hash = block_hash
                
                if self.blockchain.add_block(candidate):
                    self.blocks_mined += 1
                    self._update()
                    
                    elapsed = time.time() - self.start_time
                    print(f"✅ BLOC #{len(self.blockchain.chain)} MINÉ en {elapsed:.1f}s !")
                    print(f"   Hash: {block_hash[:40]}...")
                    print(f"   Récompense: {self.blockchain.reward()} VEIL")
                    
                    if self.callback:
                        self.callback(candidate)
                    
                    return candidate
            
            if time.time() - last_print > 3:
                self._update()
                elapsed = time.time() - self.start_time
                print(f"   ⛏️  {self.stats['hashrate']:.0f} H/s | {elapsed:.0f}s | Nonce: {candidate.header.nonce:,}")
                last_print = time.time()
        
        return None

    def start_mining(self, addr):
        self.is_mining = True
        print(f"⚡ Minage démarré pour {addr[:20]}...")
        print(f"   Objectif: 1 bloc toutes les 2 minutes")
        print(f"   Récompense: {self.blockchain.reward()} VEIL/bloc")
        print()
        
        def loop():
            while self.is_mining:
                try:
                    block = self.mine_block(addr)
                    if block:
                        print(f"🎉 +{self.blockchain.reward()} VEIL !\n")
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
