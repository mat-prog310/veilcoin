let currentWallet = null;

async function createWallet() {
    const name = document.getElementById('create-name').value.trim();
    if (!name) return alert('Nom requis');
    const res = await fetch('/api/wallet/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    });
    const data = await res.json();
    if (data.success) {
        document.getElementById('create-result').innerHTML = `
            <div class="alert alert-success">
                ✅ Wallet créé !<br>
                <strong>Seed phrase :</strong><br>
                <code>${data.seed_phrase}</code>
            </div>`;
        document.getElementById('login-name').value = name;
        document.getElementById('login-seed').value = data.seed_phrase;
    }
}

async function loginWallet() {
    const name = document.getElementById('login-name').value.trim();
    const seed = document.getElementById('login-seed').value.trim();
    if (!name || !seed) return alert('Nom et seed requis');
    const res = await fetch('/api/wallet/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, seed_phrase: seed})
    });
    const data = await res.json();
    if (data.success) {
        currentWallet = data.name;
        document.getElementById('wallet-connected').classList.remove('d-none');
        document.getElementById('wallet-address').textContent = data.address.substring(0, 20) + '...';
        loadBalance();
    }
}

async function loadBalance() {
    if (!currentWallet) return;
    const res = await fetch(`/api/wallet/${currentWallet}/balance`);
    const data = await res.json();
    document.getElementById('wallet-balance').textContent = data.balance_veil.toFixed(4);
    document.getElementById('wallet-eur').textContent = '€' + data.balance_eur.toFixed(6);
}

async function logoutWallet() {
    await fetch('/api/wallet/logout', {method: 'POST'});
    currentWallet = null;
    document.getElementById('wallet-connected').classList.add('d-none');
}
