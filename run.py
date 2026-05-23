#!/usr/bin/env python3
"""
VeilCoin - Cryptomonnaie confidentielle avec minage CPU
Point d'entrée principal
"""
import sys
import argparse
from core.blockchain import Blockchain
from core.wallet import VeilWallet
from core.randomx_miner import RandomXMiner
from config import Config

def print_banner():
    """Affiche la bannière VeilCoin"""
    banner = """
    ╔══════════════════════════════════════════════╗
    ║         🌫️  VEILCOIN - Privacy First  🌫️      ║
    ║     Mine Simply. Transact Privately.         ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)

def create_wallet(args):
    """Crée un nouveau wallet"""
    wallet = VeilWallet(args.name)
    print(f"\n✨ Wallet créé avec succès !")
    print(f"📫 Adresse publique : {wallet.address}")
    print(f"🔑 Clé publique : {wallet.public_key.hex()[:32]}...")
    print(f"\n⚠️  GARDEZ VOTRE CLÉ PRIVÉE EN SÉCURITÉ !")
    print(f"🔐 Clé privée : {wallet.private_key.hex()[:32]}...")
    print(f"   Sauvegardée dans : data/wallet_{args.name}.json")

def start_mining(args):
    """Démarre le minage"""
    print_banner()
    
    # Initialiser la blockchain
    blockchain = Blockchain()
    blockchain.print_chain()
    
    # Charger le wallet du mineur
    try:
        wallet = VeilWallet(args.wallet)
    except FileNotFoundError:
        print(f"❌ Wallet '{args.wallet}' non trouvé. Créez-le d'abord :")
        print(f"   python run.py create-wallet --name {args.wallet}")
        return
    
    # Démarrer le mineur
    miner = RandomXMiner(blockchain)
    
    print(f"\n💰 Adresse de minage : {wallet.address[:16]}...")
    print(f"🎯 Difficulté cible : {blockchain.difficulty}")
    print(f"⏱️  Temps de bloc cible : {Config.BLOCK_TIME} secondes")
    print(f"💎 Récompense actuelle : {blockchain.calculate_block_reward()} VEIL")
    print(f"\n⚡ Appuyez sur Ctrl+C pour arrêter le minage\n")
    
    try:
        while True:
            # Miner un bloc
            block = miner.mine_block(wallet.address)
            
            if block:
                print(f"\n🎉 Félicitations ! Bloc miné !")
                print(f"💎 Récompense : {blockchain.calculate_block_reward()} VEIL")
                print(f"📊 Solde du mineur : {blockchain.get_balance(wallet.address)} VEIL")
                
                # Continuer à miner
                if not args.once:
                    print(f"\n⚡ Démarrage du minage du prochain bloc...\n")
                    miner = RandomXMiner(blockchain)  # Réinitialiser pour nouveau bloc
                else:
                    break
    except KeyboardInterrupt:
        print("\n\n🛑 Minage arrêté par l'utilisateur")
        miner.stop_mining()

def check_balance(args):
    """Vérifie le solde d'un wallet"""
    blockchain = Blockchain()
    
    try:
        wallet = VeilWallet(args.wallet)
        balance = blockchain.get_balance(wallet.address)
        
        print(f"\n💰 Solde du wallet '{args.wallet}' :")
        print(f"   Adresse : {wallet.address}")
        print(f"   Solde : {balance} VEIL")
        print(f"   Hauteur de la blockchain : {len(blockchain.chain)} blocs")
    except FileNotFoundError:
        print(f"❌ Wallet '{args.wallet}' non trouvé")

def show_blockchain(args):
    """Affiche les informations de la blockchain"""
    blockchain = Blockchain()
    blockchain.print_chain()

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='🌫️  VeilCoin - Cryptomonnaie confidentielle',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python run.py create-wallet --name mon_wallet
  python run.py mine --wallet mon_wallet
  python run.py balance --wallet mon_wallet
  python run.py blockchain
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande : create-wallet
    wallet_parser = subparsers.add_parser('create-wallet', help='Créer un nouveau wallet')
    wallet_parser.add_argument('--name', type=str, default='default', 
                               help='Nom du wallet (default: default)')
    
    # Commande : mine
    mine_parser = subparsers.add_parser('mine', help='Démarrer le minage')
    mine_parser.add_argument('--wallet', type=str, required=True,
                             help='Nom du wallet pour recevoir les récompenses')
    mine_parser.add_argument('--once', action='store_true',
                             help='Miner un seul bloc puis arrêter')
    
    # Commande : balance
    balance_parser = subparsers.add_parser('balance', help='Vérifier le solde')
    balance_parser.add_argument('--wallet', type=str, required=True,
                                help='Nom du wallet')
    
    # Commande : blockchain
    blockchain_parser = subparsers.add_parser('blockchain', 
                                              help='Afficher les informations de la blockchain')
    
    args = parser.parse_args()
    
    # Exécuter la commande appropriée
    if args.command == 'create-wallet':
        create_wallet(args)
    elif args.command == 'mine':
        start_mining(args)
    elif args.command == 'balance':
        check_balance(args)
    elif args.command == 'blockchain':
        show_blockchain(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
