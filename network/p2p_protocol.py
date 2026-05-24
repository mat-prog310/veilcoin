import json

class P2PProtocol:
    @staticmethod
    def create_message(msg_type, data):
        return json.dumps({'type': msg_type, 'data': data, 'protocol': 'veilcoin/1.0'})

    @staticmethod
    def parse_message(raw):
        try:
            return json.loads(raw)
        except:
            return None

    @staticmethod
    def ping():
        return P2PProtocol.create_message('ping', {})

    @staticmethod
    def new_block(block_data):
        return P2PProtocol.create_message('new_block', block_data)

    @staticmethod
    def new_transaction(tx_data):
        return P2PProtocol.create_message('new_tx', tx_data)
