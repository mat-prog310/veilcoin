from .block import Block

class Consensus:
    @staticmethod
    def validate_block(block, chain):
        return block.is_valid() and (not chain or block.header.previous_hash == chain[-1].block_hash)

    @staticmethod
    def is_chain_valid(chain):
        return all(Consensus.validate_block(chain[i], chain[:i]) for i in range(1, len(chain)))

    @staticmethod
    def resolve_fork(chains):
        valid = [c for c in chains if Consensus.is_chain_valid(c)]
        return max(valid, key=lambda c: (len(c), sum(b.header.difficulty for b in c))) if valid else None
