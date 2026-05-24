import hashlib
import json
import time
from typing import List, Dict, Any

class TransactionInput:
    def __init__(self, ring_members, key_image, signature, amount=0):
        self.ring_members = ring_members
        self.key_image = key_image
        self.signature = signature
        self.amount = amount
    def to_dict(self):
        return {'ring_members': self.ring_members, 'key_image': self.key_image, 'signature': self.signature, 'amount': self.amount}

class TransactionOutput:
    def __init__(self, stealth_address, amount, encrypted_amount=None):
        self.stealth_address = stealth_address
        self.amount = amount
        self.encrypted_amount = encrypted_amount or hashlib.sha256(f"veil_{amount}".encode()).hexdigest()
        self.index = 0
    def to_dict(self):
        return {'stealth_address': self.stealth_address, 'amount': self.amount, 'encrypted_amount': self.encrypted_amount, 'index': self.index}

class VeilTransaction:
    def __init__(self, inputs, outputs, fee=0.001, extra=None):
        self.version = 1
        self.inputs = inputs
        self.outputs = outputs
        self.fee = fee
        self.extra = extra or b''
        self.timestamp = time.time()
        self.tx_id = self._txid()
        self.confirmations = 0

    def _txid(self):
        return hashlib.sha256(json.dumps({'version': self.version, 'inputs': [i.to_dict() for i in self.inputs], 'outputs': [o.to_dict() for o in self.outputs], 'fee': self.fee, 'timestamp': self.timestamp}, sort_keys=True).encode()).hexdigest()

    def to_dict(self):
        return {'version': self.version, 'tx_id': self.tx_id, 'inputs': [i.to_dict() for i in self.inputs], 'outputs': [o.to_dict() for o in self.outputs], 'fee': self.fee, 'timestamp': self.timestamp, 'confirmations': self.confirmations}

    def is_valid(self):
        return bool(self.inputs and self.outputs)

    def get_total_output(self):
        return sum(o.amount for o in self.outputs)
