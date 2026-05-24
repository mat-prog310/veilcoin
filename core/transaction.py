import hashlib, json, time

class TransactionInput:
    def __init__(self, ring_members, key_image, signature, amount=0):
        self.ring_members = ring_members
        self.key_image = key_image
        self.signature = signature
        self.amount = amount

    def to_dict(self):
        return {'ring_members': self.ring_members, 'key_image': self.key_image,
                'signature': self.signature, 'amount': self.amount}

class TransactionOutput:
    def __init__(self, stealth_address, amount, encrypted_amount=None):
        self.stealth_address = stealth_address
        self.amount = amount
        self.encrypted_amount = encrypted_amount or hashlib.sha256(f"veil_{amount}".encode()).hexdigest()

    def to_dict(self):
        return {'stealth_address': self.stealth_address, 'amount': self.amount,
                'encrypted_amount': self.encrypted_amount}

class VeilTransaction:
    def __init__(self, inputs, outputs, fee=0.001):
        self.inputs = inputs
        self.outputs = outputs
        self.fee = fee
        self.burn_address = "BURN_ADDRESS_0000000000000000000000000000000000000000"
        
        # 🔥 1% de frais brûlés
        total_out = sum(o.amount for o in outputs)
        self.burn_fee = total_out * 0.01
        
        if self.burn_fee > 0:
            burn_output = TransactionOutput(self.burn_address, self.burn_fee)
            self.outputs.append(burn_output)
        
        self.timestamp = time.time()
        self.tx_id = self._txid()
        self.confirmations = 0

    def _txid(self):
        d = {'inputs': [i.to_dict() for i in self.inputs],
             'outputs': [o.to_dict() for o in self.outputs],
             'fee': self.fee, 'timestamp': self.timestamp}
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

    def to_dict(self):
        return {'tx_id': self.tx_id,
                'inputs': [i.to_dict() for i in self.inputs],
                'outputs': [o.to_dict() for o in self.outputs],
                'fee': self.fee, 'burn_fee': self.burn_fee,
                'timestamp': self.timestamp, 'confirmations': self.confirmations}

    def is_valid(self):
        return bool(self.inputs and self.outputs)
