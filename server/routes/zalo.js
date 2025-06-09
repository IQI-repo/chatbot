const express = require('express');
const router = express.Router();
const zaloCtrl = require('../controllers/zaloController');

router.post('/webhook', zaloCtrl.handleWebhook);

module.exports = router;