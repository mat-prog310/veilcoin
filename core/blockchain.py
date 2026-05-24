import hashlib, json, os, time
from config import Config
from .block import Block
from .transaction import VeilTransaction, TransactionInput, TransactionOutput

class Blockchain:
    def __init__(self, data_dir=Config.DATA_DIR):
        self.data_dir = data_dir
        self.chain = []
        self.mempool = []
        self.difficulty = Config.INITIAL_DIFFICULTY
        self.last_block_time = time.time()
        os.makedirs(data_dir, exist_ok=True)
        self.load()

    def load(self):
        p = os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    d = json.load(f)
                    self.chain = [Block.from_dict(b) for b in d.get('blocks', [])]
                    self.difficulty = d.get('current_difficulty', Config.INITIAL_DIFFICULTY)
            except:
                self.genesis()
        else:
            self.genesis()

    def genesis(self):
        gi = TransactionInput(["GENESIS"], "GENESIS_KEY", "GENESIS_SIG", 0)
        go = TransactionOutput("GENESIS_ADDR", Config.BASE_REWARD)
        tx = VeilTransaction([gi], [go], 0)
        tx.tx_id = "0" * 64
        b = Block(1, "0" * 64, [tx], 1)
        b.header.nonce = 0
        b.block_hash = hashlib.sha256(json.dumps(b.header.to_dict()).encode()).hexdigest()
        self.chain.append(b)
        self.save()

    def add_block(self, b):
        if self.chain and b.header.previous_hash != self.chain[-1].block_hash: return False
        if not b.is_valid(): return False
        self.chain.append(b)
        if len(self.chain) % Config.DIFFICULTY_ADJUSTMENT_INTERVAL == 0: self.adjust()
        self.save()
        return True

    def create_new_block(self, addr):
        miner_reward = 25
        pool_reward = 25
        
        ci1 = TransactionInput(["COINBASE"], f"CB_MINER_{len(self.chain)}_{time.time()}", "CB_SIG", 0)
        co1 = TransactionOutput(addr, miner_reward)
        tx1 = VeilTransaction([ci1], [co1], 0)
        
        ci2 = TransactionInput(["COINBASE"], f"CB_POOL_{len(self.chain)}_{time.time()}", "CB_SIG", 0)
        co2 = TransactionOutput("POOL_ADDRESS", pool_reward)
        tx2 = VeilTransaction([ci2], [co2], 0)
        
        return Block(1, self.chain[-1].block_hash if self.chain else "0" * 64, [tx1, tx2] + self.mempool[:20], self.difficulty)

    def reward(self): return 50

    def adjust(self):
        if len(self.chain) < Config.DIFFICULTY_ADJUSTMENT_INTERVAL: return
        r = self.chain[-Config.DIFFICULTY_ADJUSTMENT_INTERVAL:]
        t = r[-1].header.timestamp - r[0].header.timestamp
        e = Config.BLOCK_TIME * Config.DIFFICULTY_ADJUSTMENT_INTERVAL
        if t < e / 2: self.difficulty += 1
        elif t > e * 2: self.difficulty = max(1, self.difficulty - 1)
        self.save()

    def save(self):
        with open(os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE), 'w') as f:
            json.dump({'blocks': [b.to_dict() for b in self.chain], 'current_difficulty': self.difficulty}, f, indent=2)

    def get_stats(self):
        supply = sum(b.transactions[0].outputs[0].amount for b in self.chain)
        burned = sum(out.amount for b in self.chain for tx in b.transactions for out in tx.outputs if "BURN" in out.stealth_address)
        return {
            'height': len(self.chain),
            'difficulty': self.difficulty,
            'total_supply': supply,
            'total_burned': burned,
            'mempool_size': len(self.mempool),
            'current_reward': 50
        }

    def get_recent_blocks(self, n=10):
        return [b.to_dict() for b in self.chain[-n:]]
