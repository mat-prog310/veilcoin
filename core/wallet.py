{% extends "base.html" %}
{% block title %}VeilCoin - Wallet{% endblock %}
{% block content %}
<div class="container">
    <h1 class="mb-4"><i class="fas fa-wallet text-success"></i> Wallet</h1>

    <div class="row">
        <div class="col-md-6 mb-3">
            <div class="card bg-dark">
                <div class="card-body">
                    <h5 class="card-title"><i class="fas fa-plus-circle"></i> Créer un wallet</h5>
                    <div class="mb-3">
                        <label class="form-label">Nom du wallet</label>
                        <input type="text" id="create-name" class="form-control" placeholder="mon_wallet">
                    </div>
                    <button class="btn btn-success w-100" onclick="createWallet()">
                        <i class="fas fa-plus"></i> Créer
                    </button>
                    <div id="create-result" class="mt-3"></div>
                </div>
            </div>
        </div>

        <div class="col-md-6 mb-3">
            <div class="card bg-dark">
                <div class="card-body">
                    <h5 class="card-title"><i class="fas fa-sign-in-alt"></i> Se connecter</h5>
                    <div class="mb-3">
                        <label class="form-label">Nom du wallet</label>
                        <input type="text" id="login-name" class="form-control" placeholder="mon_wallet">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Seed Phrase (12 mots)</label>
                        <textarea id="login-seed" class="form-control" rows="2" placeholder="entrez vos 12 mots secrets..."></textarea>
                    </div>
                    <button class="btn btn-primary w-100" onclick="loginWallet()">
                        <i class="fas fa-unlock"></i> Se connecter
                    </button>
                    <div id="login-result" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>

    <div id="wallet-connected" class="d-none">
        <div class="row">
            <div class="col-md-4 mb-3">
                <div class="card bg-dark border-success">
                    <div class="card-body text-center">
                        <h5>Adresse</h5>
                        <code id="wallet-address" class="text-success"></code>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="card bg-dark border-info">
                    <div class="card-body text-center">
                        <h5>Solde VEIL</h5>
                        <h2 id="wallet-balance" class="text-info">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-3">
                <div class="card bg-dark border-warning">
                    <div class="card-body text-center">
                        <h5>Valeur en €</h5>
                        <h2 id="wallet-eur" class="text-warning">€0</h2>
                    </div>
                </div>
            </div>
        </div>
        <button class="btn btn-outline-danger mb-3" onclick="logoutWallet()">
            <i class="fas fa-sign-out-alt"></i> Déconnexion
        </button>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
let currentWallet = null;

async function createWallet() {
    const name = document.getElementById('create-name').value.trim();
    if (!name) {
        alert('Nom requis');
        return;
    }

    console.log('Création wallet:', name);

    try {
        const res = await fetch('/api/wallet/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name})
        });

        const data = await res.json();
        console.log('Réponse:', data);

        if (data.success) {
            document.getElementById('create-result').innerHTML = `
                <div class="alert alert-success">
                    <strong>✅ Wallet créé !</strong><br>
                    <small>Adresse : ${(data.address || '').substring(0, 20)}...</small><br><br>
                    <strong>🔐 SEED PHRASE :</strong><br>
                    <code class="bg-dark p-2 rounded d-block mt-1">${data.seed_phrase}</code><br>
                    <small class="text-danger">⚠️ Sauvegardez-la précieusement !</small>
                </div>
            `;
            document.getElementById('login-name').value = name;
            document.getElementById('login-seed').value = data.seed_phrase;
        } else {
            document.getElementById('create-result').innerHTML = `
                <div class="alert alert-danger">❌ ${data.error || 'Erreur inconnue'}</div>
            `;
        }
    } catch (e) {
        console.error('Erreur:', e);
        document.getElementById('create-result').innerHTML = `
            <div class="alert alert-danger">❌ Erreur de connexion au serveur</div>
        `;
    }
}

async function loginWallet() {
    const name = document.getElementById('login-name').value.trim();
    const seed = document.getElementById('login-seed').value.trim();

    if (!name || !seed) {
        alert('Nom et seed phrase requis');
        return;
    }

    try {
        const res = await fetch('/api/wallet/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, seed_phrase: seed})
        });

        const data = await res.json();
        console.log('Login:', data);

        if (data.success) {
            currentWallet = data.name;
            document.getElementById('wallet-connected').classList.remove('d-none');
            document.getElementById('wallet-address').textContent = (data.address || '').substring(0, 20) + '...';
            loadBalance();
            document.getElementById('login-result').innerHTML = '';
        } else {
            document.getElementById('login-result').innerHTML = `
                <div class="alert alert-danger">❌ ${data.error || 'Erreur'}</div>
            `;
        }
    } catch (e) {
        document.getElementById('login-result').innerHTML = `
            <div class="alert alert-danger">❌ Erreur de connexion</div>
        `;
    }
}

async function loadBalance() {
    if (!currentWallet) return;

    try {
        const res = await fetch(`/api/wallet/${currentWallet}/balance`);
        const data = await res.json();
        document.getElementById('wallet-balance').textContent = (data.balance_veil || 0).toFixed(4);
        document.getElementById('wallet-eur').textContent = '€' + (data.balance_eur || 0).toFixed(6);
    } catch (e) {
        console.error('Erreur balance:', e);
    }
}

async function logoutWallet() {
    try {
        await fetch('/api/wallet/logout', {method: 'POST'});
    } catch (e) {}
    currentWallet = null;
    document.getElementById('wallet-connected').classList.add('d-none');
}
</script>
{% endblock %}
