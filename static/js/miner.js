const socket = io();

async function startMining() {
    const wallet = document.getElementById('miner-wallet').value;
    await fetch('/api/miner/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({wallet})
    });
    document.getElementById('start-btn').disabled = true;
    document.getElementById('stop-btn').disabled = false;
    document.getElementById('mining-status').innerHTML = '<div class="alert alert-success">⛏️ Minage en cours...</div>';
}

async function stopMining() {
    await fetch('/api/miner/stop');
    document.getElementById('start-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
    document.getElementById('mining-status').innerHTML = '<div class="alert alert-secondary">⚪ Arrêté</div>';
}

socket.on('miner_stats', (s) => {
    const el = document.getElementById('hashrate');
    if (el) el.textContent = Math.round(s.hashrate);
    const el2 = document.getElementById('blocks-found');
    if (el2) el2.textContent = s.blocks_mined;
    const el3 = document.getElementById('shares');
    if (el3) el3.textContent = s.accepted_shares;
});
