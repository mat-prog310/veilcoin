// Socket.IO connection
const socket = io();
socket.on('connect', () => console.log('Connected'));
