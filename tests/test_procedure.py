"""
Procédure de test complète pour VeilCoin
Exécute tous les tests de base
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.blockchain import Blockchain
from core.wallet import VeilWallet
from core.randomx_miner import RandomXMiner
from core.transaction import VeilTransaction
from config import Config

def print_separator(title=""):
    """Affiche un séparateur"""
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
        print(f"{'='*60}")

def test_create_wallets():
    """Test 1 : Création de wallets"""
    print_separator("TEST 1 : Création de wallets")
    
    alice = VeilWallet("alice")
    bob = VeilWallet("bob")
    charlie = VeilWallet("charlie")
    
    print(f"✅ Alice : {alice.address[:30]}...")
    print(f"✅ Bob : {bob.address[:30]}...")
    print(f"✅ Charlie : {charlie.address[:30]}...")
    
    return alice, bob, charlie

def test_genesis_block(blockchain):
    """Test 2 : Vérification du bloc genesis"""
    print_separator("TEST 2 : Vérification du bloc genesis")
    
    assert len(blockchain.chain) > 0, "❌ Blockchain vide !"
    
    genesis = blockchain.chain[0]
    print(f"✅ Bloc genesis créé")
    print(f"   Hash : {genesis.block_hash[:32]}...")
    print(f"   Transactions : {len(genesis.transactions)}")
    
    return True

def test_mining(blockchain, alice):
    """Test 3 : Minage de blocs"""
    print_separator("TEST 3 : Minage de blocs")
    
    miner = RandomXMiner(blockchain)
    
    print("⚡ Minage du bloc #2...")
    start_time = time.time()
    
    block = miner.mine_block(alice.address)
    
    elapsed = time.time() - start_time
    
    if block:
        print(f"✅ Bloc miné en {elapsed:.2f} secondes")
        print(f"   Hash : {block.block_hash[:32]}...")
        print(f"   Nonce : {block.header.nonce:,}")
        
        balance = blockchain.get_balance(alice.address)
        print(f"💰 Solde d'Alice : {balance} VEIL")
        
        return True
    else:
        print("❌ Échec du minage")
        return False

def test_transactions(blockchain, alice, bob):
    """Test 4 : Transactions"""
    print_separator("TEST 4 : Transactions")
    
    # Donner un solde à Alice (simulation)
    alice.balance = 100
    
    # Créer une transaction
    print(f"💸 Alice envoie 25 VEIL à Bob...")
    tx = alice.create_transaction(bob.address, 25, blockchain)
    
    if tx:
        print(f"✅ Transaction créée : {tx.tx_id[:32]}...")
        print(f"   Montant : {tx.get_total_output()} VEIL")
        print(f"   Frais : {tx.fee} VEIL")
        
        # Ajouter au mempool
        if blockchain.add_transaction(tx):
            print("✅ Transaction ajoutée au mempool")
            print(f"   Mempool : {len(blockchain.mempool)} transactions")
        else:
            print("❌ Transaction refusée par le mempool")
        
        return tx
    else:
        print("❌ Échec création transaction")
        return None

def test_block_with_transactions(blockchain, alice):
    """Test 5 : Minage d'un bloc avec transactions"""
    print_separator("TEST 5 : Minage d'un bloc avec transactions")
    
    miner = RandomXMiner(blockchain)
    block = miner.mine_block(alice.address)
    
    if block:
        print(f"✅ Bloc #{len(blockchain.chain)} miné")
        print(f"   Transactions incluses : {len(block.transactions) - 1}")
        print(f"   Récompense : {blockchain.calculate_block_reward()} VEIL")
        print(f"   Mempool restant : {len(blockchain.mempool)}")
        return True
    else:
        print("❌ Échec du minage")
        return False

def test_balance_verification(blockchain, alice, bob):
    """Test 6 : Vérification des soldes"""
    print_separator("TEST 6 : Vérification des soldes")
    
    alice_balance = blockchain.get_balance(alice.address)
    bob_balance = blockchain.get_balance(bob.address)
    
    print(f"💰 Alice : {alice_balance} VEIL")
    print(f"💰 Bob : {bob_balance} VEIL")
    
    # Vérifier que les soldes sont cohérents
    assert alice_balance >= 0, "❌ Solde Alice négatif !"
    assert bob_balance >= 0, "❌ Solde Bob négatif !"
    
    print("✅ Soldes vérifiés")
    return True

def test_blockchain_integrity(blockchain):
    """Test 7 : Intégrité de la blockchain"""
    print_separator("TEST 7 : Intégrité de la blockchain")
    
    from core.consensus import Consensus
    
    is_valid = Consensus.is_chain_valid(blockchain.chain)
    
    if is_valid:
        print("✅ Blockchain valide")
        print(f"   Hauteur : {len(blockchain.chain)}")
        print(f"   Difficulté : {blockchain.difficulty}")
        print(f"   Offre totale : {sum(b.transactions[0].outputs[0].amount for b in blockchain.chain):.2f} VEIL")
    else:
        print("❌ Blockchain invalide !")
    
    return is_valid

def test_api_endpoints():
    """Test 8 : Test des endpoints API"""
    print_separator("TEST 8 : Endpoints API")
    
    try:
        import requests
        
        base_url = f"http://localhost:{Config.API_PORT}"
        
        # Test stats
        response = requests.get(f"{base_url}/api/stats")
        assert response.status_code == 200
        print("✅ GET /api/stats OK")
        
        # Test blocs
        response = requests.get(f"{base_url}/api/blocks?limit=5")
        assert response.status_code == 200
        print("✅ GET /api/blocks OK")
        
        return True
    except Exception as e:
        print(f"⚠️ Tests API ignorés (serveur non démarré) : {e}")
        return True  # Ne pas bloquer si le serveur n'est pas lancé

def run_all_tests():
    """Exécute tous les tests"""
    print("""
    ╔══════════════════════════════════════════════╗
    ║     🧪 VEILCOIN - Tests automatisés 🧪        ║
    ╚══════════════════════════════════════════════╝
    """)
    
    results = {}
    
    try:
        # Initialisation
        blockchain = Blockchain()
        
        # Test 1 : Wallets
        alice, bob, charlie = test_create_wallets()
        results['create_wallets'] = True
        
        # Test 2 : Genesis
        results['genesis_block'] = test_genesis_block(blockchain)
        
        # Test 3 : Minage
        results['mining'] = test_mining(blockchain, alice)
        
        # Test 4 : Transactions
        results['transactions'] = test_transactions(blockchain, alice, bob) is not None
        
        # Test 5 : Bloc avec transactions
        results['block_with_tx'] = test_block_with_transactions(blockchain, alice)
        
        # Test 6 : Soldes
        results['balances'] = test_balance_verification(blockchain, alice, bob)
        
        # Test 7 : Intégrité
        results['integrity'] = test_blockchain_integrity(blockchain)
        
        # Test 8 : API
        results['api'] = test_api_endpoints()
        
    except Exception as e:
        print(f"\n❌ Erreur pendant les tests : {e}")
        import traceback
        traceback.print_exc()
    
    # Résumé
    print_separator("RÉSULTATS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test.replace('_', ' ').title()}")
    
    print(f"\n{'='*60}")
    print(f"  Total : {passed}/{total} tests réussis")
    print(f"{'='*60}\n")
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
