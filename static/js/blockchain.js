const socket = io();

socket.on('recent_blocks', (blocks) => {
    const tbody = document.getElementById('blocks-table');
    if (!tbody) return;
    tbody.innerHTML = '';
    blocks.reverse().forEach((b, i) => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${i + 1}</td>
            <td><code>${(b.block_hash || '').substring(0, 20)}...</code></td>
            <td>${b.transactions ? b.transactions.length : 0}</td>
            <td class="text-success">${b.transactions?.[0]?.outputs?.[0]?.amount || 0} VEIL</td>
        `;
    });
});
