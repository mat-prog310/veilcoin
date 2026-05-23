"""
Mineur RandomX pour VeilCoin
RandomX est un algorithme de Proof of Work optimisé pour les CPU
Il est ASIC-resistant et FPGA-resistant
"""
import hashlib
import os
import struct
import time
from typing import Optional

class RandomXMiner:
    """Mineur CPU utilisant RandomX (implémentation simplifiée)"""
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.is_mining = False
        self.hashrate = 0
        self.start_time = 0
        self.hashes_computed = 0
    
    def randomx_hash(self, header_bytes: bytes, nonce: int) -> bytes:
        """
        Fonction de hachage RandomX simplifiée
        En production, utiliser la bibliothèque randomx complète
        """
        # Simulation de RandomX avec SHA3 et opérations mémoire
        ctx = hashlib.sha3_512()
        
        # Phase 1 : Mélange initial
        ctx.update(header_bytes)
        ctx.update(struct.pack('<Q', nonce))
        initial_hash = ctx.digest()
        
        # Phase 2 : Opérations pseudo-aléatoires mémoire-intensive
        scratchpad = bytearray(262144)  # 256 KB de scratchpad (RandomX réel utilise 2GB)
        
        for i in range(0, len(scratchpad), 64):
            chunk = hashlib.sha3_256(initial_hash + i.to_bytes(4, 'little')).digest()
            scratchpad[i:i+32] = chunk[:32]
        
        # Phase 3 : Compression finale
        final_ctx = hashlib.sha3_256()
        for i in range(0, len(scratchpad), 64):
            final_ctx.update(scratchpad[i:i+64])
        
        return final_ctx.digest()
    
    def mine_block(self, miner_address: str, max_attempts: int = None) -> Optional[dict]:
        """
        Mine un nouveau bloc
        
        Args:
            miner_address: Adresse du mineur pour la récompense
            max_attempts: Nombre maximum de tentatives (None = infini)
        
        Returns:
            Le bloc miné ou None si échec
        """
        print(f"⚡ Démarrage du minage VeilCoin - Algorithme RandomX")
        print(f"   Mineur : {miner_address[:16]}...")
        print(f"   Difficulté : {self.blockchain.difficulty}")
        
        # Créer le bloc candidat
        candidate_block = self.blockchain.create_new_block(miner_address)
        if not candidate_block:
            print("❌ Impossible de créer un bloc candidat")
            return None
        
        target = "0" * self.blockchain.difficulty
        self.start_time = time.time()
        self.hashes_computed = 0
        self.is_mining = True
        
        while self.is_mining:
            # Incrémenter le nonce
            candidate_block.header.nonce += 1
            
            # Préparer l'en-tête pour le hachage
            header_bytes = self.serialize_header(candidate_block.header.to_dict())
            
            # Calculer le hash avec RandomX
            block_hash_bytes = self.randomx_hash(header_bytes, candidate_block.header.nonce)
            block_hash = block_hash_bytes.hex()
            
            self.hashes_computed += 1
            
            # Vérifier si le hash correspond à la difficulté
            if block_hash.startswith(target):
                candidate_block.block_hash = block_hash
                elapsed = time.time() - self.start_time
                
                print(f"\n✅ BLOC MINÉ !")
                print(f"   Hash : {block_hash}")
                print(f"   Nonce : {candidate_block.header.nonce}")
                print(f"   Temps : {elapsed:.2f} secondes")
                print(f"   Hashrate : {self.get_hashrate():.2f} H/s")
                
                self.is_mining = False
                
                # Ajouter le bloc à la blockchain
                if self.blockchain.add_block(candidate_block):
                    # Vider le mempool des transactions incluses
                    included_tx_ids = [tx.tx_id for tx in candidate_block.transactions[1:]]
                    self.blockchain.mempool = [
                        tx for tx in self.blockchain.mempool 
                        if tx.tx_id not in included_tx_ids
                    ]
                    self.blockchain.save_mempool()
                    
                    return candidate_block.to_dict()
                else:
                    print("❌ Échec de l'ajout du bloc")
                    return None
            
            # Afficher la progression toutes les 100K tentatives
            if candidate_block.header.nonce % 100000 == 0:
                elapsed = time.time() - self.start_time
                print(f"   🔄 Nonce: {candidate_block.header.nonce:,} | "
                      f"Hashrate: {self.get_hashrate():.2f} H/s | "
                      f"Temps: {elapsed:.1f}s")
            
            # Arrêter si max_attempts est atteint
            if max_attempts and candidate_block.header.nonce >= max_attempts:
                print(f"❌ Arrêt après {max_attempts:,} tentatives")
                self.is_mining = False
                return None
        
        return None
    
    def serialize_header(self, header_dict: dict) -> bytes:
        """Sérialise l'en-tête du bloc en bytes pour le hachage"""
        # Format simplifié : concaténer les champs importants
        data = (
            header_dict['version'].to_bytes(4, 'little') +
            bytes.fromhex(header_dict['previous_hash']) +
            bytes.fromhex(header_dict['merkle_root']) +
            struct.pack('<d', header_dict['timestamp']) +
            header_dict['difficulty'].to_bytes(4, 'little')
        )
        return data
    
    def get_hashrate(self) -> float:
        """Calcule le hashrate actuel"""
        if self.hashes_computed == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        
        return self.hashes_computed / elapsed
    
    def stop_mining(self):
        """Arrête le minage"""
        self.is_mining = False
        print("🛑 Minage arrêté")
