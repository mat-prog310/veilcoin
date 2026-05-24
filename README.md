# 🌫️ VeilCoin (VEIL)

> **Mine Simply. Transact Privately.**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)](https://github.com/mat-prog310/veilcoin)
[![Render](https://img.shields.io/badge/Live-Render-brightgreen)](https://veilcoin-fvzp.onrender.com)

---

## 📜 Copyright
© 2026 VeilCoin - Tous droits réservés.
Créé par DevOfVeil (github.com/mat-prog310)

Ce logiciel est protégé par les lois internationales sur le droit d'auteur.
Toute reproduction ou distribution non autorisée est strictement interdite.

---

## 🛡️ Qu'est-ce que VeilCoin ?

**VeilCoin** est un réseau blockchain décentralisé inspiré de **Bitcoin**, mais conçu dès le départ pour offrir :

- 🔒 **Confidentialité maximale** : Transactions intraçables grâce aux **Ring Signatures** et **Stealth Addresses**
- 🛡️ **Sécurité renforcée** : Algorithme **SHA256 Proof of Work** avec mécanisme de **Double Hash**
- ⛏️ **Minage équitable** : **ASIC-resistant**, minable sur n'importe quel PC (même ancien)
- 💰 **Supply limitée** : **25 000 000 VEIL** maximum (comme Bitcoin avec ses 21M)
- 🤝 **100% P2P** : Échanges directs entre utilisateurs via **PayPal**, sans intermédiaire

---

## 🏗️ Architecture

| Composant | Technologie |
|-----------|-------------|
| **Blockchain** | Propriétaire (inspirée Bitcoin) |
| **Consensus** | Proof of Work (SHA256 Double Hash) |
| **Confidentialité** | Ring Signatures + Stealth Addresses |
| **Paiements** | P2P PayPal (email caché jusqu'à double blocage) |
| **Protection marché** | Anti pump/dump (±10% max par transaction) |
| **Minage** | CPU-friendly, ASIC-resistant |

---

## 📊 Spécifications Techniques

| Paramètre | Valeur |
|-----------|--------|
| **Nom** | VeilCoin |
| **Symbole** | VEIL |
| **Supply maximale** | 25 000 000 VEIL |
| **Récompense par bloc** | 50 VEIL |
| **Halving** | Tous les 210 000 blocs |
| **Temps de bloc cible** | ~2 minutes |
| **Algorithme** | SHA256 Double Hash avec sel aléatoire |
| **Difficulté** | Ajustement automatique tous les 10 blocs |
| **Portefeuille** | Seed phrase BIP39 (12 mots) |

---

## 🌐 Accès au Réseau

| Service | URL |
|---------|-----|
| **Dashboard** | [veilcoin-fvzp.onrender.com](https://veilcoin-fvzp.onrender.com) |
| **Wallet** | [veilcoin-fvzp.onrender.com/wallet](https://veilcoin-fvzp.onrender.com/wallet) |
| **Mineur Web** | [veilcoin-fvzp.onrender.com/miner](https://veilcoin-fvzp.onrender.com/miner) |
| **Marché P2P** | [veilcoin-fvzp.onrender.com/market](https://veilcoin-fvzp.onrender.com/market) |
| **Blockchain Explorer** | [veilcoin-fvzp.onrender.com/blockchain](https://veilcoin-fvzp.onrender.com/blockchain) |

---

## ⚡ Installation Rapide

### Prérequis
- **Python 3.11** ou supérieur
- **pip** (gestionnaire de paquets Python)
- **Git** (optionnel)

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/mat-prog310/veilcoin.git

# 2. Aller dans le dossier
cd veilcoin

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le serveur
python app.py

Puis ouvrir http://localhost:5000 dans le navigateur.

⛏️ Mineur Terminal
Un mineur en ligne de commande est disponible pour les mineurs sérieux :

bash
# Lancer le mineur terminal
python miner.py
Créer un exécutable (.exe)
bash
# Avec PyInstaller
pip install pyinstaller
pyinstaller --onefile --name VeilCoin_Miner miner.py
# L'exe sera dans dist/VeilCoin_Miner.exe

# Avec cx_Freeze
pip install cx_Freeze
python setup.py build
# L'exe sera dans build/exe.win-amd64-3.11/VeilCoin_Miner.exe
🔐 Système de Sécurité
VeilCoin utilise une architecture de sécurité multi-couches :

Couche	Mécanisme	Protection contre
1	Double SHA256	Attaques par collision
2	Sel aléatoire (8 bytes)	Attaques par dictionnaire
3	Proof of Work	Attaques Sybil, spam
4	Ring Signatures	Traçage des transactions
5	Stealth Addresses	Liaison des adresses
6	Double blocage P2P	Fraude PayPal
Niveau de Sécurité Réseau
text
Sécurité = Hashrate × 16^difficulté

Exemple :
- Hashrate : 10 000 H/s
- Difficulté : 3
- Sécurité : 10 000 × 4096 = 40 960 000
🤝 Comment Contribuer
⚠️ Critères d'Éligibilité
Pour participer au développement de VeilCoin, vous devez obligatoirement :

Avoir une expérience vérifiable sur au moins un des projets suivants :

🟠 Bitcoin (Core, Lightning Network, BIPs)

🟣 Solana (Programs, SPL Tokens, Validators)

🔵 Ethereum (Smart Contracts, EVM)

🟢 Monero (RingCT, Bulletproofs)

Soumettre une candidature via une Issue GitHub contenant :

📁 Portfolio blockchain (liens GitHub, commits)

🏆 Projets réalisés (avec preuves)

✍️ Lettre de motivation pour rejoindre VeilCoin

Validation par le créateur :

Toutes les Pull Requests seront examinées et validées par DevOfVeil avant d'être mergées. Cette période de validation manuelle garantit la qualité et la sécurité du code pendant la phase de lancement.

📋 Processus de Contribution
text
1. Fork le projet
2. Créer une branche (git checkout -b feature/ma-feature)
3. Commit les changements (git commit -m 'Ajout de ma feature')
4. Push la branche (git push origin feature/ma-feature)
5. Ouvrir une Pull Request
6. Attendre la validation de DevOfVeil
🗺️ Roadmap
Phase	Description	Statut
Phase 1	Blockchain + Minage + Wallet	✅ Terminé
Phase 2	Marché P2P + Intégration PayPal	✅ Terminé
Phase 3	Mineur Terminal + Sécurité réseau	✅ Terminé
Phase 4	Ring Signatures avancées (RingCT)	🔄 En cours
Phase 5	Application mobile (iOS/Android)	📅 Prévu Q3 2026
Phase 6	DEX intégré (Uniswap-style)	📅 Prévu Q4 2026
Phase 7	Governance DAO	📅 Prévu 2027
📞 Contact
Créateur : DevOfVeil

GitHub : github.com/mat-prog310

Discord : Rejoindre le serveur (bientôt)

Twitter : @VeilCoin (bientôt)
