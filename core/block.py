import hashlib
import json
import time
from typing import List
from .transaction import VeilTransaction, TransactionInput, TransactionOutput

class BlockHeader:
    def __init__(self, version, prev, merkle, ts, diff, nonce):
        self.version = version
        self.previous_hash = prev
        self.merkle_root = merkle
        self.timestamp = ts
        self.difficulty = diff
        self.nonce = nonce
    def to_dict(self):
        return {'version': self.version, 'previous_hash': self.previous_hash, 'merkle_root': self.merkle_root, 'timestamp': self.timestamp, 'difficulty': self.difficulty, 'nonce': self.nonce}

class Block:
    def __init__(self, version, prev, transactions, difficulty):
        self.header = BlockHeader(version, prev, self._merkle(transactions), time.time(), difficulty, 0)
        self.transactions = transactions
        self.block_hash = None

    def _merkle(self, txs):
        if not txs: return hashlib.sha256(b'empty').hexdigest()
        h = [tx.tx_id for tx in txs]
        while len(h) > 1:
            if len(h) % 2: h.append(h[-1])
            h = [hashlib.sha256((h[i] + h[i+1]).encode()).hexdigest() for i in range(0, len(h), 2)]
        return h[0]

    def is_valid(self):
        return self.block_hash and self.block_hash.startswith("0" * self.header.difficulty) and len(self.transactions) > 0

    def to_dict(self):
        return {'header': self.header.to_dict(), 'transactions': [tx.to_dict() for tx in self.transactions], 'block_hash': self.block_hash}

    @classmethod
    def from_dict(cls, d):
        txs = []
        for td in d.get('transactions', []):
            ins = [TransactionInput(i['ring_members'], i['key_image'], i['signature'], i.get('amount', 0)) for i in td.get('inputs', [])]
            outs = [TransactionOutput(o['stealth_address'], o['amount'], o.get('encrypted_amount', '')) for o in td.get('outputs', [])]
            tx = VeilTransaction(ins, outs, td.get('fee', 0))
            tx.tx_id = td.get('tx_id', tx.tx_id)
            tx.timestamp = td.get('timestamp', tx.timestamp)
            txs.append(tx)
        b = cls(d['header']['version'], d['header']['previous_hash'], txs, d['header']['difficulty'])
        b.header.nonce = d['header']['nonce']
        b.header.timestamp = d['header']['timestamp']
        b.header.merkle_root = d['header']['merkle_root']
        b.block_hash = d['block_hash']
        return b
