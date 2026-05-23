import hashlib
import json
import time
from typing import List, Optional
from .transaction import VeilTransaction

class BlockHeader:
    """En-tête de bloc VeilCoin"""
    def __init__(self, version: int, previous_hash: str, merkle_root: str,
                 timestamp: float, difficulty: int, nonce: int):
        self.version = version
        self.previous_hash = previous_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce

    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }

class Block:
    """Bloc complet de la blockchain VeilCoin"""
    
    def __init__(self, version: int, previous_hash: str, 
                 transactions: List[VeilTransaction], difficulty: int):
        self.header = BlockHeader(
            version=version,
            previous_hash=previous_hash,
            merkle_root=self.compute_merkle_root(transactions),
            timestamp=time.time(),
            difficulty=difficulty,
            nonce=0
        )
        self.transactions = transactions
        self.block_hash = None
    
    def compute_merkle_root(self, transactions: List[VeilTransaction]) -> str:
        """Calcule la racine de Merkle des transactions"""
        if not transactions:
            return hashlib.sha3_256(b'empty_block').hexdigest()
        
        tx_hashes = [tx.tx_id for tx in transactions]
        
        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            
            new_level = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i+1]
                new_hash = hashlib.sha3_256(combined.encode()).hexdigest()
                new_level.append(new_hash)
            
            tx_hashes = new_level
        
        return tx_hashes[0]
    
    def mine_block(self) -> None:
        """Mine le bloc en trouvant un nonce valide (Proof of Work)"""
        target = "0" * self.header.difficulty
        
        while True:
            self.header.nonce += 1
            block_data = json.dumps(self.header.to_dict(), sort_keys=True)
            block_hash = hashlib.sha3_256(block_data.encode()).hexdigest()
            
            if block_hash.startswith(target):
                self.block_hash = block_hash
                print(f"✅ Bloc miné ! Nonce: {self.header.nonce}")
                print(f"   Hash: {self.block_hash}")
                break
            
            if self.header.nonce % 100000 == 0:
                print(f"   Minage en cours... Nonce: {self.header.nonce}")
    
    def is_valid(self) -> bool:
        """Vérifie la validité du bloc"""
        # Vérifier le hash
        block_data = json.dumps(self.header.to_dict(), sort_keys=True)
        computed_hash = hashlib.sha3_256(block_data.encode()).hexdigest()
        
        if computed_hash != self.block_hash:
            return False
        
        # Vérifier la preuve de travail
        target = "0" * self.header.difficulty
        if not self.block_hash.startswith(target):
            return False
        
        # Vérifier le Merkle root
        if self.compute_merkle_root(self.transactions) != self.header.merkle_root:
            return False
        
        # Vérifier chaque transaction
        for tx in self.transactions:
            if not tx.is_valid():
                return False
        
        return True
    
    def to_dict(self) -> dict:
        return {
            'header': self.header.to_dict(),
            'transactions': [tx.to_dict() for tx in self.transactions],
            'block_hash': self.block_hash
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Block':
        """Reconstruit un bloc depuis un dictionnaire"""
        from .transaction import TransactionInput, TransactionOutput
        
        transactions = []
        for tx_data in data['transactions']:
            inputs = [TransactionInput(**inp) for inp in tx_data['inputs']]
            outputs = [TransactionOutput(**out) for out in tx_data['outputs']]
            tx = VeilTransaction(inputs, outputs)
            tx.tx_id = tx_data['tx_id']
            transactions.append(tx)
        
        block = cls(
            version=data['header']['version'],
            previous_hash=data['header']['previous_hash'],
            transactions=transactions,
            difficulty=data['header']['difficulty']
        )
        block.header.nonce = data['header']['nonce']
        block.header.timestamp = data['header']['timestamp']
        block.header.merkle_root = data['header']['merkle_root']
        block.block_hash = data['block_hash']
        
        return block
