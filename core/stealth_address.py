import hashlib
import os
from cryptography.hazmat.primitives.asymmetric import ec

class StealthAddress:
    @staticmethod
    def generate_keypair():
        pk = ec.generate_private_key(ec.SECP256R1())
        pub = pk.public_key()
        return pk.private_numbers().private_value.to_bytes(32, 'big'), pub.public_numbers().x.to_bytes(32, 'big')

    @staticmethod
    def generate_stealth_address(receiver_pub, sender_priv=None):
        if sender_priv is None:
            sender_priv = os.urandom(32)
        shared = hashlib.sha256(sender_priv + receiver_pub).digest()
        return {'stealth_address': hashlib.sha256(shared + b'veilcoin_stealth').hexdigest()}
