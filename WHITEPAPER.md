# VEILCOIN WHITEPAPER v1.0

## Une cryptomonnaie déflationniste, 100% P2P, sans exchange centralisé

---

## 📑 SOMMAIRE

1. [Introduction](#1-introduction)
2. [Tokenomics - Brûlage Extrême](#2-tokenomics---brûlage-extrême)
3. [Minage](#3-minage)
4. [Marché P2P](#4-marché-p2p)
5. [Sécurité](#5-sécurité)
6. [Feuille de Route](#6-feuille-de-route)
7. [Conclusion](#7-conclusion)

---

## 1. INTRODUCTION

VeilCoin est une cryptomonnaie déflationniste conçue pour être **équitable, sécurisée et 100% P2P**.

**Principes fondamentaux :**
- ❌ Pas d'exchange centralisé (Binance, Coinbase, etc.)
- ❌ Pas de pool de liquidité externe
- ❌ Pas de trésorerie
- ✅ 100% des échanges en P2P direct
- ✅ Brûlage progressif de 97.5% de la supply

---

## 2. TOKENOMICS - BRÛLAGE EXTRÊME

### Spécifications Techniques

| Paramètre | Valeur |
|-----------|--------|
| Nom | VeilCoin |
| Symbole | VEIL |
| Supply initiale | 1 000 000 000 VEIL |
| Supply finale | **25 000 000 VEIL** |
| Taux de brûlage | **97.5%** |
| Consensus | Proof of Work (PoW) |
| Récompense par bloc | 50 VEIL |

### 🔥 Mécanisme de Brûlage

Chaque transaction (envoi, vente, transfert P2P) génère **1% de frais** :

| Composant | Pourcentage | Destination |
|-----------|-------------|-------------|
| Brûlage | 0.5% | Définitivement détruit |
| Mineur | 0.5% | Récompense du bloc |

### Objectif : 25 000 000 VEIL
Supply initiale : 1 000 000 000 VEIL
↓
🔥 BRÛLAGE PROGRESSIF 🔥
↓
Supply finale : 25 000 000 VEIL
VEIL brûlés : 975 000 000 VEIL (97.5%)

text

### Évolution de la Supply

| Étape | Supply | VEIL brûlés |
|-------|--------|-------------|
| Départ | 1 000 000 000 | 0 |
| Phase 1 | 500 000 000 | 500 000 000 |
| Phase 2 | 250 000 000 | 750 000 000 |
| Phase 3 | 100 000 000 | 900 000 000 |
| Phase 4 | 50 000 000 | 950 000 000 |
| **Objectif** | **25 000 000** | **975 000 000** |

### Pourquoi 25M seulement ?

- **Rareté maximale** : Offre ultra-limitée
- **Déflation intégrée** : Chaque transaction augmente la valeur
- **Économie P2P** : Pas besoin de millions de tokens
- **Protection anti-inflation** : Supply qui diminue avec le temps

---

## 3. MINAGE

### Conditions Obligatoires

| Condition | Valeur |
|-----------|--------|
| Staking requis | **200 VEIL** minimum |
| Blocs max/heure | 5 blocs par wallet |
| Cooldown | 1 heure après limite |
| Blocs max à vie | 1000 blocs par wallet |

### Récompense

- **50 VEIL** par bloc trouvé
- Distribution immédiate
- Vérification double avant récompense

### Protection Anti-Ferme
❌ FERME DE MINAGE IMPOSSIBLE ❌

Les grandes fermes de minage ne peuvent pas exister sur VeilCoin grâce à :

Staking obligatoire (200 VEIL = coût d'entrée)

Rate limiting strict (5 blocs/heure)

Cooldown obligatoire (1h après 5 blocs)

Limite à vie (1000 blocs max)

text

### Pénalités pour Triche

| Infraction | Sanction |
|------------|----------|
| Tentative de minage avec wallet banni | Confiscation des 200 VEIL stakés |
| Wallet banni | Réputation à 0 + blacklist |
| IP bannie | Accès totalement bloqué |

---

## 4. MARCHÉ P2P

### Aucun Exchange Centralisé

VeilCoin **n'est et ne sera jamais listé** sur des exchanges centralisés (Binance, Coinbase, Kraken, etc.).

**Tous les échanges se font via :**

| Méthode | Description |
|---------|-------------|
| 🤝 Marché P2P intégré | Achat/vente direct entre utilisateurs |
| 📸 Preuve de paiement | Upload de capture PayPal |
| 🔒 Système d'escrow | VEIL bloqués jusqu'à confirmation |
| ⭐ Réputation | Score de confiance (0-100) |

### Workflow d'une Transaction P2P
┌─────────────────────────────────────────────────────────┐
│ ÉTAPE 1 : Vendeur crée une offre (statut: open) │
│ ↓ │
│ ÉTAPE 2 : Acheteur match l'offre (statut: matched) │
│ ↓ │
│ ÉTAPE 3 : Acheteur paie via PayPal │
│ ↓ │
│ ÉTAPE 4 : Acheteur upload la preuve (statut: pending) │
│ ↓ │
│ ÉTAPE 5 : Vendeur accepte la preuve (statut: paid) │
│ ↓ │
│ ÉTAPE 6 : Vendeur libère les VEIL (statut: completed) │
└─────────────────────────────────────────────────────────┘

text

### Système de Réputation (0-100)

| Score | Statut | Droits |
|-------|--------|--------|
| 80-100 | 🟢 Excellent | Trading illimité |
| 50-79 | 🟡 Bon | Trading standard |
| 20-49 | 🟠 Limité | Vérification renforcée |
| 1-19 | 🔴 Suspect | Surveillance active |
| 0 | ⚫ Banni | Accès total bloqué |

### Évolution du Score

| Action | Impact |
|--------|--------|
| Transaction complétée | **+2 points** |
| Transaction échouée | **-25 points** |
| Signalement reçu | **-15 points** |

---

## 5. SÉCURITÉ

### Système de Blacklist

| Type | Cible | Effet |
|------|-------|-------|
| Mining Ban | Wallet | Impossible de miner |
| IP Ban | Adresse IP | Accès total bloqué |
| Wallet Ban | Wallet | Trading + transactions bloqués |

### Anti-Manipulation du Marché

| Protection | Valeur |
|------------|--------|
| Prix minimum de vente | **0.015€** (prix floor) |
| Transaction max | 5% de la pool |
| Cooldown entre trades | 60 secondes |
| Anti-dump | Limite de blocs de trading |

### Cas de Bannissement

- **Self-purchase manipulation** : Achat de ses propres tokens
- **Matched pattern détecté** : Comportement frauduleux avéré
- **Triche au minage** : Tentative de contournement
- **Défaut de paiement répété** : Non-respect des engagements

### Admin - Force Recovery

En cas de litige, l'administrateur peut :
- 🔄 Forcer le transfert de VEIL
- 🔄 Récupérer des fonds
- 🔄 Régler les conflits P2P

---

## 6. FEUILLE DE ROUTE

### ✅ Phase 1 - Lancement (Terminé)

- [x] Blockchain fonctionnelle
- [x] Wallet natif
- [x] Minage avec staking 200 VEIL
- [x] Marché P2P basique

### ✅ Phase 2 - Sécurité (Terminé)

- [x] Anti-farm (5 blocs/heure)
- [x] Cooldown 1 heure
- [x] Blacklist IP et Wallet
- [x] Système de réputation
- [x] Anti-manipulation du marché
- [x] Prix floor (0.015€)

### 🔄 Phase 3 - Optimisation (En cours)

- [x] Preuves de paiement chiffrées AES-256
- [x] Système d'escrow complet
- [x] Résolution des litiges
- [ ] Application mobile

### 📅 Phase 4 - Objectif 25M

- [ ] Supply réduite à 25 000 000 VEIL
- [ ] Brûlage de 975 000 000 VEIL atteint
- [ ] Communauté autonome
- [ ] Documentation complète

---

## 7. CONCLUSION

VeilCoin est une cryptomonnaie unique qui combine :

| Caractéristique | Avantage |
|-----------------|----------|
| 🔥 Brûlage 97.5% | Rareté extrême, valeur croissante |
| ⛏️ Staking 200 VEIL | Anti-spam, donne de la valeur |
| 🛡️ Anti-farm | Protection des petits mineurs |
| 🤝 P2P uniquement | Pas de dépendance aux exchanges |
| ⭐ Réputation | Confiance entre utilisateurs |
| 🔒 Escrow | Transactions sécurisées |

### Pourquoi VeilCoin ?

- ✅ **100% décentralisé** : Pas d'entité centrale
- ✅ **100% P2P** : Les utilisateurs échangent directement
- ✅ **100% déflationniste** : Supply qui diminue toujours
- ✅ **Anti-ferme** : Équité pour tous les mineurs

### Liens Utiles

- 🌐 **Site web** : https://veilcoin.xyz
- 🤝 **Marché P2P** : https://veilcoin.xyz/p2p
- ⛏️ **Blockchain Explorer** : https://veilcoin.xyz/blockchain
- 👛 **Wallet** : https://veilcoin.xyz/wallet

---

*VeilCoin - La crypto qui brûle 97.5% de sa supply.*

*© 2026 VeilCoin. Tous droits réservés.*
