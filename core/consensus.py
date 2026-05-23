"""
Mécanisme de consensus pour VeilCoin
Vérifie les règles de consensus lors de l'ajout de blocs
"""
from typing import List
from .block import Block
from .transaction import VeilTransaction

class Consensus:
    """Vérificateur de consensus"""
    
    @staticmethod
    def validate_block(block: Block, chain: List[Block]) -> bool:
        """
        Valide un bloc selon les règles de consensus VeilCoin
        
        Règles :
        1. Le bloc doit avoir un hash valide
        2. La preuve de travail doit être valide
        3. Le previous_hash doit correspondre au dernier bloc
        4. Les transactions doivent être valides
        5. La récompense de bloc doit être correcte
        6. Pas de doubles dépenses via key_images
        """
        # Règle 1 & 2 : Vérifier le hash et la PoW
        if not block.is_valid():
            return False
        
        # Règle 3 : Previous hash
        if block.header.previous_hash != chain[-1].block_hash:
            return False
        
        # Règle 4 : Transactions valides
        for tx in block.transactions:
            if not tx.is_valid():
                return False
        
        # Règle 5 : Vérifier la récompense de bloc
        coinbase_tx = block.transactions[0]
        expected_reward = Consensus.calculate_expected_reward(len(chain))
        
        actual_reward = sum(
            out.amount for out in coinbase_tx.outputs
        )
        
        if actual_reward > expected_reward:
            return False
        
        # Règle 6 : Pas de doubles dépenses
        key_images_seen = set()
        
        for block in chain:
            for tx in block.transactions:
                for inp in tx.inputs:
                    key_images_seen.add(inp.key_image)
        
        for tx in block.transactions:
            for inp in tx.inputs:
                if inp.key_image in key_images_seen:
                    return False
                key_images_seen.add(inp.key_image)
        
        return True
    
    @staticmethod
    def calculate_expected_reward(height: int, base_reward: float = 50.0) -> float:
        """Calcule la récompense attendue avec halving"""
        halvings = height // 210000
        reward = base_reward / (2 ** halvings)
        return reward
    
    @staticmethod
    def resolve_fork(chains: List[List[Block]]) -> List[Block]:
        """
        Résout une fourche en choisissant la chaîne la plus longue (et valide)
        En cas d'égalité, choisit celle avec le plus de travail cumulé
        """
        valid_chains = []
        
        for chain in chains:
            if Consensus.is_chain_valid(chain):
                valid_chains.append(chain)
        
        if not valid_chains:
            return None
        
        # Trier par longueur, puis par travail cumulé
        return max(valid_chains, key=lambda c: (
            len(c),
            sum(b.header.difficulty for b in c)
        ))
    
    @staticmethod
    def is_chain_valid(chain: List[Block]) -> bool:
        """Vérifie la validité d'une chaîne entière"""
        for i in range(1, len(chain)):
            if not Consensus.validate_block(chain[i], chain[:i]):
                return False
        return True
