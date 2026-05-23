import json
import os
from typing import List, Optional
from .block import Block
from .transaction import VeilTransaction
from config import Config

class Blockchain:
    """La blockchain VeilCoin avec support de la confidentialité"""
    
    def __init__(self, data_dir: str = Config.DATA_DIR):
        self.data_dir = data_dir
        self.chain: List[Block] = []
        self.mempool: List[VeilTransaction] = []
        self.difficulty = Config.INITIAL_DIFFICULTY
        
        # Créer le dossier data si nécessaire
        os.makedirs(data_dir, exist_ok=True)
        
        # Charger la blockchain existante ou créer le bloc genesis
        self.load_blockchain()
    
    def load_blockchain(self) -> None:
        """Charge la blockchain depuis le fichier"""
        blockchain_path = os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE)
        
        if os.path.exists(blockchain_path):
            with open(blockchain_path, 'r') as f:
                data = json.load(f)
                self.chain = [Block.from_dict(b) for b in data['blocks']]
                self.difficulty = data['current_difficulty']
            print(f"📦 Blockchain chargée : {len(self.chain)} blocs")
        else:
            self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Crée le bloc genesis avec un message spécial"""
        print("🌱 Création du bloc genesis VeilCoin...")
        
        # Transaction coinbase spéciale
        from .transaction import TransactionInput, TransactionOutput
        
        genesis_input = TransactionInput(
            ring_members=["GENESIS"],
            key_image="GENESIS_KEY_IMAGE",
            signature="GENESIS_SIGNATURE"
        )
        
        genesis_output = TransactionOutput(
            stealth_address="GENESIS_STEALTH_ADDRESS",
            amount=Config.BASE_REWARD,
            encrypted_amount="GENESIS_ENCRYPTED"
        )
        
        genesis_tx = VeilTransaction(
            inputs=[genesis_input],
            outputs=[genesis_output],
            extra=b"VeilCoin Genesis Block - Privacy for All"
        )
        
        genesis_block = Block(
            version=1,
            previous_hash="0" * 64,
            transactions=[genesis_tx],
            difficulty=self.difficulty
        )
        
        # Miner le bloc genesis
        print("⚡ Minage du bloc genesis...")
        genesis_block.mine_block()
        
        self.chain.append(genesis_block)
        self.save_blockchain()
        print("✅ Bloc genesis créé avec succès !")
    
    def add_block(self, block: Block) -> bool:
        """Ajoute un bloc miné à la blockchain"""
        # Vérifier que le bloc est valide
        if not block.is_valid():
            print("❌ Bloc invalide !")
            return False
        
        # Vérifier que le previous_hash correspond
        if block.header.previous_hash != self.chain[-1].block_hash:
            print("❌ Le previous_hash ne correspond pas au dernier bloc !")
            return False
        
        # Ajouter le bloc
        self.chain.append(block)
        
        # Ajuster la difficulté si nécessaire
        if len(self.chain) % Config.DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
            self.adjust_difficulty()
        
        # Sauvegarder
        self.save_blockchain()
        return True
    
    def add_transaction_to_mempool(self, transaction: VeilTransaction) -> bool:
        """Ajoute une transaction au mempool si elle est valide"""
        if not transaction.is_valid():
            print("❌ Transaction invalide !")
            return False
        
        # Vérifier les doubles dépenses via key_images
        for tx in self.mempool:
            for inp in tx.inputs:
                for new_inp in transaction.inputs:
                    if inp.key_image == new_inp.key_image:
                        print("❌ Double dépense détectée !")
                        return False
        
        self.mempool.append(transaction)
        self.save_mempool()
        print(f"📝 Transaction ajoutée au mempool : {transaction.tx_id[:16]}...")
        return True
    
    def create_new_block(self, miner_address: str) -> Optional[Block]:
        """Crée un nouveau bloc candidat pour le minage"""
        if len(self.mempool) == 0:
            print("⚠️ Aucune transaction dans le mempool")
            return None
        
        # Sélectionner les transactions du mempool
        selected_txs = self.mempool[:10]  # Limite à 10 tx par bloc pour l'exemple
        
        # Créer la transaction coinbase (récompense du mineur)
        from .transaction import TransactionInput, TransactionOutput
        
        coinbase_input = TransactionInput(
            ring_members=["COINBASE"],
            key_image=f"COINBASE_{len(self.chain)}",
            signature="COINBASE_SIGNATURE"
        )
        
        coinbase_output = TransactionOutput(
            stealth_address=miner_address,
            amount=self.calculate_block_reward(),
            encrypted_amount="ENCRYPTED_COINBASE"
        )
        
        coinbase_tx = VeilTransaction(
            inputs=[coinbase_input],
            outputs=[coinbase_output],
            extra=f"Block {len(self.chain) + 1} Reward".encode()
        )
        
        # Ajouter la coinbase au début
        all_transactions = [coinbase_tx] + selected_txs
        
        # Créer le bloc
        new_block = Block(
            version=1,
            previous_hash=self.chain[-1].block_hash,
            transactions=all_transactions,
            difficulty=self.difficulty
        )
        
        return new_block
    
    def calculate_block_reward(self) -> float:
        """Calcule la récompense de bloc avec halving"""
        halvings = len(self.chain) // 210000
        reward = Config.BASE_REWARD / (2 ** halvings)
        return min(reward, Config.BASE_REWARD)
    
    def adjust_difficulty(self) -> None:
        """Ajuste la difficulté de minage toutes les N blocs"""
        if len(self.chain) < Config.DIFFICULTY_ADJUSTMENT_INTERVAL:
            return
        
        recent_blocks = self.chain[-Config.DIFFICULTY_ADJUSTMENT_INTERVAL:]
        time_diff = recent_blocks[-1].header.timestamp - recent_blocks[0].header.timestamp
        expected_time = Config.BLOCK_TIME * Config.DIFFICULTY_ADJUSTMENT_INTERVAL
        
        if time_diff < expected_time / 2:
            self.difficulty += 1
            print(f"📈 Difficulté augmentée à {self.difficulty}")
        elif time_diff > expected_time * 2:
            self.difficulty = max(1, self.difficulty - 1)
            print(f"📉 Difficulté réduite à {self.difficulty}")
    
    def save_blockchain(self) -> None:
        """Sauvegarde la blockchain dans un fichier JSON"""
        data = {
            'blocks': [block.to_dict() for block in self.chain],
            'current_difficulty': self.difficulty,
            'height': len(self.chain)
        }
        
        filepath = os.path.join(self.data_dir, Config.BLOCKCHAIN_FILE)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save_mempool(self) -> None:
        """Sauvegarde le mempool"""
        filepath = os.path.join(self.data_dir, Config.MEMPOOL_FILE)
        with open(filepath, 'w') as f:
            json.dump([tx.to_dict() for tx in self.mempool], f, indent=2)
    
    def get_balance(self, wallet_address: str) -> float:
        """Calcule le solde d'une adresse (version simplifiée)"""
        balance = 0.0
        
        for block in self.chain:
            for tx in block.transactions:
                for output in tx.outputs:
                    # Dans la vraie version, on scannerait les adresses furtives
                    if output.stealth_address == wallet_address:
                        balance += output.amount
        
        return balance
    
    def print_chain(self) -> None:
        """Affiche les informations de la blockchain"""
        print(f"\n{'='*60}")
        print(f"🔗 VeilCoin Blockchain - Hauteur : {len(self.chain)}")
        print(f"   Difficulté actuelle : {self.difficulty}")
        print(f"   Mempool : {len(self.mempool)} transactions en attente")
        
        for i, block in enumerate(self.chain[-3:], 1):  # Affiche les 3 derniers blocs
            print(f"\n📦 Bloc #{len(self.chain) - 3 + i}")
            print(f"   Hash : {block.block_hash[:32]}...")
            print(f"   Transactions : {len(block.transactions)}")
            print(f"   Nonce : {block.header.nonce}")
        
        print(f"{'='*60}\n")
