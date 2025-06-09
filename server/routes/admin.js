const express = require('express');
const router = express.Router();
const adminController = require('../controllers/adminController');
router.get('/messages', adminController.getMessages);
module.exports = router;