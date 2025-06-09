const express = require('express');
const router = express.Router();
const zaloPController = require('../controllers/zaloPersonalController');

router.post('/webhook', zaloPController.gatewayWebhook);

module.exports = router;