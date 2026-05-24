const socket = io();

socket.on('connect', () => {
    console.log('Connected to VeilCoin');
});

socket.on('blockchain_stats', (data) => {
    const el = document.getElementById('height');
    if (el) el.textContent = data.height;
    const el2 = document.getElementById('supply');
    if (el2) el2.textContent = data.total_supply.toFixed(0);
    const el3 = document.getElementById('difficulty');
    if (el3) el3.textContent = data.difficulty;
    const el4 = document.getElementById('reward');
    if (el4) el4.textContent = data.current_reward;
});

socket.on('miner_stats', (data) => {
    const el = document.getElementById('hashrate');
    if (el) el.textContent = Math.round(data.hashrate);
    const el2 = document.getElementById('blocks-found');
    if (el2) el2.textContent = data.blocks_mined;
});

socket.on('recent_blocks', (blocks) => {
    const tbody = document.getElementById('recent-blocks');
    if (!tbody) return;
    tbody.innerHTML = '';
    blocks.reverse().forEach((b, i) => {
        const row = tbody.insertRow();
        row.innerHTML = `<td>${i+1}</td><td><code>${(b.block_hash||'').substring(0,20)}...</code></td><td>${b.transactions?b.transactions.length:0}</td>`;
    });
});
