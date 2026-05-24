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
        self.stats = {'hashrate': 0, 'total_hashes': 0, 'blocks_mined': 0, 'current_difficulty': blockchain.difficulty, 'accepted_shares': 0}

    def set_callback(self, cb):
        self.callback = cb

    def _update_stats(self):
        if self.start_time > 0:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.stats['hashrate'] = self.total_hashes / elapsed
                self.stats['total_hashes'] = self.total_hashes
                self.stats['blocks_mined'] = self.blocks_mined
                self.stats['current_difficulty'] = self.blockchain.difficulty

    def mine_block(self, miner_address):
        candidate = self.blockchain.create_new_block(miner_address)
        if not candidate:
            return None
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.total_hashes = 0
        self.is_mining = True
        last_print = time.time()
        while self.is_mining:
            candidate.header.nonce += 1
            self.total_hashes += 1
            h = hashlib.sha256(str(candidate.header.to_dict()).encode() + candidate.header.nonce.to_bytes(8, 'big')).hexdigest()
            if h.startswith(target):
                candidate.block_hash = h
                if self.blockchain.add_block(candidate):
                    self.blocks_mined += 1
                    self._update_stats()
                    if self.callback:
                        self.callback(candidate)
                    return candidate
            if time.time() - last_print > 5:
                self._update_stats()
                print(f"   {self.stats['hashrate']:.0f} H/s | Nonce: {candidate.header.nonce:,}")
                last_print = time.time()
        return None

    def start_mining(self, addr):
        self.is_mining = True
        def loop():
            while self.is_mining:
                self.mine_block(addr)
                time.sleep(0.5)
        self.mining_thread = threading.Thread(target=loop, daemon=True)
        self.mining_thread.start()

    def stop_mining(self):
        self.is_mining = False

    def get_stats(self):
        self._update_stats()
        return self.stats
