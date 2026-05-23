import hashlib
import json
import time
from typing import List, Optional

class TransactionInput:
    """Entrée de transaction avec signature en anneau (ring signature)"""
    def __init__(self, ring_members: List[str], key_image: str, signature: str):
        self.ring_members = ring_members  # Liste des clés publiques dans l'anneau
        self.key_image = key_image  # Empêche la double dépense sans révéler l'expéditeur
        self.signature = signature  # Preuve que le signataire est dans l'anneau

    def to_dict(self):
        return {
            'ring_members': self.ring_members,
            'key_image': self.key_image,
            'signature': self.signature
        }

class TransactionOutput:
    """Sortie de transaction avec adresse furtive (stealth address)"""
    def __init__(self, stealth_address: str, amount: float, encrypted_amount: str):
        self.stealth_address = stealth_address  # Adresse furtive unique pour cette transaction
        self.amount = amount  # Montant en clair (sera chiffré en production)
        self.encrypted_amount = encrypted_amount  # Montant chiffré (Range Proof simplifiée)

    def to_dict(self):
        return {
            'stealth_address': self.stealth_address,
            'amount': self.amount,
            'encrypted_amount': self.encrypted_amount
        }

class VeilTransaction:
    """Transaction confidentielle VeilCoin"""
    def __init__(self, inputs: List[TransactionInput], outputs: List[TransactionOutput], 
                 extra: Optional[bytes] = None):
        self.version = 1
        self.inputs = inputs
        self.outputs = outputs
        self.extra = extra or b''  # Données supplémentaires (messages chiffrés, etc.)
        self.timestamp = time.time()
        self.tx_id = self.compute_txid()

    def compute_txid(self) -> str:
        """Calcule l'identifiant unique de la transaction"""
        tx_data = {
            'version': self.version,
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'extra': self.extra.hex(),
            'timestamp': self.timestamp
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha3_256(tx_string.encode()).hexdigest()

    def to_dict(self):
        return {
            'version': self.version,
            'tx_id': self.tx_id,
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'extra': self.extra.hex(),
            'timestamp': self.timestamp
        }

    def is_valid(self) -> bool:
        """Vérifie la validité basique de la transaction"""
        if not self.inputs or not self.outputs:
            return False
        if len(self.tx_id) != 64:  # SHA3-256 produit 64 caractères hex
            return False
        return True
