"""
Mineur VeilCoin - SHA256 simple + Difficulté 5
Temps estimé : 5-30 minutes par bloc
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

    def _hash(self, data):
        """SHA256 simple = plus rapide"""
        return hashlib.sha256(data).hexdigest()

    def mine_block(self, addr):
        candidate = self.blockchain.create_new_block(addr)
        if not candidate:
            return None
        
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.total_hashes = 0
        self.is_mining = True
        last_print = time.time()
        
        print(f"⛏️  Bloc #{len(self.blockchain.chain)} | Difficulté: {self.blockchain.difficulty}")
        
        while self.is_mining:
            # 1000 hashes par lot = plus rapide
            for _ in range(1000):
                candidate.header.nonce += 1
                self.total_hashes += 1
                
                header_data = str(candidate.header.to_dict()).encode()
                block_hash = self._hash(
                    header_data + candidate.header.nonce.to_bytes(8, 'big')
                )
                
                if block_hash.startswith(target):
                    candidate.block_hash = block_hash
                    
                    if self.blockchain.add_block(candidate):
                        self.blocks_mined += 1
                        self._update()
                        
                        elapsed = time.time() - self.start_time
                        print(f"\n🎉 BLOC MINÉ en {elapsed/60:.1f} min ! +25 VEIL")
                        
                        if self.callback:
                            self.callback(candidate)
                        
                        return candidate
            
            if time.time() - last_print > 5:
                self._update()
                elapsed = time.time() - self.start_time
                
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
                    eta = "..."
                
                progress = min(100, (self.total_hashes / avg_needed) * 100)
                print(f"   ⛏️  {self.stats['hashrate']:.0f} H/s | {progress:.2f}% | ⏳ {eta}")
                last_print = time.time()
        
        return None

    def start_mining(self, addr):
        self.is_mining = True
        print(f"⚡ Minage démarré - Difficulté: {self.blockchain.difficulty}")
        print(f"   💰 25 VEIL/bloc | ⏱️  ~5-30 min")
        
        def loop():
            while self.is_mining:
                try:
                    block = self.mine_block(addr)
                    if block:
                        print(f"🎉 +25 VEIL !\n")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️ {e}")
                    time.sleep(2)
        
        self.mining_thread = threading.Thread(target=loop, daemon=True)
        self.mining_thread.start()

    def stop_mining(self):
        self.is_mining = False
        if self.mining_thread and self.mining_thread.is_alive():
            self.mining_thread.join(timeout=3)

    def get_stats(self):
        self._update()
        return self.stats
