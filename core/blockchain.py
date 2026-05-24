import hashlib
import json
import os
import time
from typing import List, Optional, Dict
from datetime import datetime
from .block import Block
from .transaction import VeilTransaction, TransactionInput, TransactionOutput
from config import Config

class BlockchainStats:
    def __init__(self):
        self.height = 0
        self.total_transactions = 0
        self.total_supply = 0
        self.current_difficulty = 0
        self.mempool_size = 0

class Blockchain:
    def __init__(self, data_dir=Config.DATA_DIR):
        self.data_dir = data_dir
        self.chain: List[Block] = []
        self.mempool: List[VeilTransaction] = []
        self.difficulty = Config.INITIAL_DIFFICULTY
        self.stats = BlockchainStats()
        self.last_block_time = time.time()
        os.makedirs(data_dir, exist_ok=True)
        self.load_blockchain()

    def load_blockchain(self):
        path = os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.chain = [Block.from_dict(b) for b in data.get('blocks', [])]
                    self.difficulty = data.get('current_difficulty', Config.INITIAL_DIFFICULTY)
                self._update_stats()
            except:
                self.create_genesis_block()
        else:
            self.create_genesis_block()

    def create_genesis_block(self):
        gi = TransactionInput(["GENESIS"], "GENESIS_KEY", "GENESIS_SIG", 0)
        go = TransactionOutput("GENESIS_ADDR", Config.BASE_REWARD)
        tx = VeilTransaction([gi], [go], 0)
        tx.tx_id = "0" * 64
        block = Block(1, "0" * 64, [tx], 1)
        block.header.nonce = 0
        block.block_hash = hashlib.sha256(json.dumps(block.header.to_dict()).encode()).hexdigest()
        self.chain.append(block)
        self.save_blockchain()

    def add_block(self, block):
        if len(self.chain) > 0 and block.header.previous_hash != self.chain[-1].block_hash:
            return False
        if not block.is_valid():
            return False
        self.chain.append(block)
        self.last_block_time = time.time()
        if len(self.chain) % Config.DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
            self._adjust_difficulty()
        self._update_stats()
        self.save_blockchain()
        return True

    def create_new_block(self, miner_address):
        txs = self.mempool[:20]
        ci = TransactionInput(["COINBASE"], f"CB_{len(self.chain)}_{time.time()}", "CB_SIG", 0)
        co = TransactionOutput(miner_address, self.calculate_block_reward())
        ctx = VeilTransaction([ci], [co], 0)
        return Block(1, self.chain[-1].block_hash if self.chain else "0" * 64, [ctx] + txs, self.difficulty)

    def calculate_block_reward(self):
        return Config.BASE_REWARD / (2 ** (len(self.chain) // Config.HALVING_INTERVAL))

    def _adjust_difficulty(self):
        if len(self.chain) < Config.DIFFICULTY_ADJUSTMENT_INTERVAL:
            return
        recent = self.chain[-Config.DIFFICULTY_ADJUSTMENT_INTERVAL:]
        t = recent[-1].header.timestamp - recent[0].header.timestamp
        expected = Config.BLOCK_TIME * Config.DIFFICULTY_ADJUSTMENT_INTERVAL
        if t < expected / 2: self.difficulty += 1
        elif t > expected * 2: self.difficulty = max(1, self.difficulty - 1)

    def _update_stats(self):
        self.stats.height = len(self.chain)
        self.stats.current_difficulty = self.difficulty
        self.stats.mempool_size = len(self.mempool)
        self.stats.total_transactions = sum(len(b.transactions) for b in self.chain)
        self.stats.total_supply = sum(b.transactions[0].outputs[0].amount for b in self.chain)

    def get_balance(self, addr):
        return sum(out.amount for b in self.chain for tx in b.transactions for out in tx.outputs if addr in out.stealth_address)

    def get_recent_blocks(self, n=10):
        return [b.to_dict() for b in self.chain[-n:]]

    def save_blockchain(self):
        with open(os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE), 'w') as f:
            json.dump({'blocks': [b.to_dict() for b in self.chain], 'current_difficulty': self.difficulty, 'height': len(self.chain)}, f, indent=2)

    def get_stats(self):
        self._update_stats()
        return {'height': self.stats.height, 'difficulty': self.stats.current_difficulty, 'total_transactions': self.stats.total_transactions, 'total_supply': self.stats.total_supply, 'mempool_size': self.stats.mempool_size, 'current_reward': self.calculate_block_reward()}
