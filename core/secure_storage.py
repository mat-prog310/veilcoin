# core/secure_storage.py
import os
import json
import base64
import time
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class SecureStorage:
    """Stockage ultra-sécurisé pour données sensibles (AES-256)"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.secure_dir = os.path.join(data_dir, "secure")
        os.makedirs(self.secure_dir, exist_ok=True)
        self.master_key = None
    
    def derive_key(self, password, salt):
        """Dérive une clé AES-256 (100k itérations - anti brute force)"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def init_master_key(self, admin_seed):
        """Initialise la clé maître depuis la seed admin"""
        salt = b'veilcoin_master_salt_2024'
        self.master_key = self.derive_key(admin_seed, salt)
        return self.master_key
    
    def encrypt(self, data, password=None):
        """Chiffre des données"""
        if password is None:
            if not self.master_key:
                raise ValueError("Master key not initialized")
            key = self.master_key
            salt = None
        else:
            salt = secrets.token_bytes(32)
            key = self.derive_key(password, salt)
        
        f = Fernet(key)
        if isinstance(data, dict):
            data = json.dumps(data)
        encrypted = f.encrypt(data.encode())
        
        if salt:
            return {'data': encrypted.decode(), 'salt': base64.b64encode(salt).decode()}
        return encrypted.decode()
    
    def decrypt(self, encrypted_data, password=None, salt=None):
        """Déchiffre des données"""
        try:
            if password is None:
                if not self.master_key:
                    raise ValueError("Master key not initialized")
                key = self.master_key
            else:
                key = self.derive_key(password, base64.b64decode(salt))
            
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_data.encode())
            try:
                return json.loads(decrypted.decode())
            except:
                return decrypted.decode()
        except:
            return None
    
    def store_payment_proof(self, order_id, buyer, image_base64, admin_seed):
        """Stocke une preuve de paiement de manière sécurisée"""
        self.init_master_key(admin_seed)
        proof_data = {
            'order_id': order_id,
            'buyer': buyer,
            'timestamp': time.time(),
            'image': image_base64
        }
        encrypted = self.encrypt(proof_data)
        filename = f"{order_id}_{int(time.time())}.enc"
        filepath = os.path.join(self.secure_dir, filename)
        with open(filepath, 'w') as f:
            f.write(encrypted)
        return filename
    
    def get_payment_proof(self, filename, admin_seed):
        """Récupère une preuve de paiement (admin seulement)"""
        self.init_master_key(admin_seed)
        filepath = os.path.join(self.secure_dir, filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r') as f:
            encrypted = f.read()
        return self.decrypt(encrypted)