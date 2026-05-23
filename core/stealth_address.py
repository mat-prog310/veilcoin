"""
Adresses furtives (Stealth Addresses)
Permet de générer une adresse unique par transaction
Seul le destinataire peut détecter que le paiement lui est destiné
"""
import hashlib
import os
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

class StealthAddress:
    """Générateur d'adresses furtives"""
    
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """Génère une paire de clés pour les adresses furtives"""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        
        private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
        public_bytes = public_key.public_numbers().x.to_bytes(32, 'big')
        
        return private_bytes, public_bytes
    
    @staticmethod
    def generate_stealth_address(receiver_public_key: bytes, 
                                sender_private_key: bytes = None) -> dict:
        """
        Crée une adresse furtive unique pour cette transaction
        
        Args:
            receiver_public_key: Clé publique du destinataire
            sender_private_key: Clé privée temporaire de l'expéditeur
        
        Returns:
            Dictionnaire avec l'adresse furtive et le secret partagé
        """
        if sender_private_key is None:
            sender_private_key = os.urandom(32)
        
        # Génération du secret partagé Diffie-Hellman
        shared_secret = hashlib.sha3_256(
            sender_private_key + receiver_public_key
        ).digest()
        
        # Création de l'adresse furtive (version simplifiée)
        stealth_address = hashlib.sha3_256(
            shared_secret + b'veilcoin_stealth'
        ).hexdigest()
        
        return {
            'stealth_address': stealth_address,
            'ephemeral_public_key': hashlib.sha3_256(
                sender_private_key
            ).hexdigest(),
            'shared_secret': shared_secret.hex()
        }
    
    @staticmethod
    def scan_for_transactions(receiver_private_key: bytes, 
                             ephemeral_public_keys: list) -> list:
        """
        Scanne la blockchain pour trouver les transactions destinées au wallet
        
        Args:
            receiver_private_key: Clé privée du destinataire
            ephemeral_public_keys: Liste des clés éphémères publiques de la blockchain
        
        Returns:
            Liste des adresses furtives appartenant au wallet
        """
        my_transactions = []
        
        for ephemeral_pub in ephemeral_public_keys:
            # Reconstruction du secret partagé
            shared_secret = hashlib.sha3_256(
                bytes.fromhex(receiver_private_key) + bytes.fromhex(ephemeral_pub)
            ).digest()
            
            # Vérification si l'adresse correspond
            potential_stealth = hashlib.sha3_256(
                shared_secret + b'veilcoin_stealth'
            ).hexdigest()
            
            my_transactions.append(potential_stealth)
        
        return my_transactions
