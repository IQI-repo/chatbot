const express = require('express');
const router = express.Router();
const fbCtrl = require('../controllers/fbController');

router.get('/webhook', fbCtrl.verifyWebhook);
router.post('/webhook', fbCtrl.handleWebhook);

module.exports = router;