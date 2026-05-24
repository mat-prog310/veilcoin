import hashlib
import os

class RingSignature:
    @staticmethod
    def generate_ring(public_keys, signer_index, private_key, message):
        ring_size = len(public_keys)
        s_values = []
        c_values = [None] * ring_size
        if signer_index != 0:
            c_values[0] = hashlib.sha256(os.urandom(32)).hexdigest()
        else:
            s_values.append(hashlib.sha256(os.urandom(32)).hexdigest())
        for i in range(ring_size):
            if i == signer_index:
                commitment = hashlib.sha256(f"{message}{private_key}{i}".encode()).hexdigest()
                c_values[i] = commitment if i == 0 else hashlib.sha256(f"{c_values[i-1]}{commitment}".encode()).hexdigest()
                s_values.append(commitment)
            else:
                s_values.append(hashlib.sha256(os.urandom(32)).hexdigest())
                if i > 0:
                    c_values[i] = hashlib.sha256(f"{c_values[i-1]}{s_values[-1]}".encode()).hexdigest()
        return {'public_keys': public_keys, 'c_values': c_values, 's_values': s_values, 'message': message}

    @staticmethod
    def verify_ring(sig):
        for i in range(len(sig['public_keys']) - 1):
            if hashlib.sha256(f"{sig['c_values'][i]}{sig['s_values'][i+1]}".encode()).hexdigest() != sig['c_values'][i+1]:
                return False
        return hashlib.sha256(f"{sig['c_values'][-1]}{sig['s_values'][0]}".encode()).hexdigest() == sig['c_values'][0]
