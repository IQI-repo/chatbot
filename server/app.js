const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const bodyParser = require('body-parser');
const path = require('path');
const { testConnection } = require('./utils/db');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8080;

app.use(cors());
app.use(bodyParser.json({limit: '15mb'}));
app.use(bodyParser.urlencoded({ extended: true, limit: '15mb' }));

app.use(express.static(path.join(__dirname, '../frontend')));
app.use('/data', express.static(path.join(__dirname, '../data')));

// Handle chat routes for client-side routing
app.get('/chat/:id', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

app.use('/api/chat', require('./routes/chat'));
app.use('/api/chat-mysql', require('./routes/chatMySql'));
app.use('/api/admin', require('./routes/admin'));
app.use('/api/menu', require('./routes/menu'));
app.use('/api/fb', require('./routes/fb'));
app.use('/api/zalo', require('./routes/zalo'));
app.use('/api/zalo-personal', require('./routes/zalo_personal'));

app.use((req, res) => res.status(404).send({error: "Not found"}));

app.listen(PORT, async () => {
  console.log(`Bot backend running at http://localhost:${PORT}`);
  // Test MySQL database connection
  await testConnection();
});