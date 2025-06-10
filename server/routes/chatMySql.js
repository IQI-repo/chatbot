const express = require('express');
const router = express.Router();
const chatMySqlController = require('../controllers/chatMySqlController');

// Chat sessions routes
router.get('/sessions/user/:user_id', chatMySqlController.getUserChatSessions);
router.post('/sessions', chatMySqlController.createChatSession);
router.put('/sessions/:session_id/end', chatMySqlController.endChatSession);
router.delete('/sessions/:session_id', chatMySqlController.deleteChatSession);

// Chat messages routes
router.get('/messages/:session_id', chatMySqlController.getChatMessages);
router.post('/messages', chatMySqlController.sendChatMessage);

// User info route
router.get('/users/:user_id', chatMySqlController.getUserInfo);

// Chat statistics route
router.get('/stats', chatMySqlController.getChatStats);

module.exports = router;
