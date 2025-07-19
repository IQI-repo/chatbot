const express = require('express');
const router = express.Router();
const adminController = require('../controllers/adminController');

/**
 * @swagger
 * tags:
 *   name: Admin
 *   description: Admin operations for the chatbot
 */

/**
 * @swagger
 * /admin/messages:
 *   get:
 *     summary: Get all chat messages for admin
 *     description: Retrieves all chat messages for administrative purposes
 *     tags: [Admin]
 *     responses:
 *       200:
 *         description: List of all chat messages
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 type: object
 *                 properties:
 *                   from:
 *                     type: string
 *                     description: Sender of the message (user or bot)
 *                   content:
 *                     type: string
 *                     description: Message content
 *                   time:
 *                     type: string
 *                     description: Timestamp of the message
 *       500:
 *         description: Server error
 */
router.get('/messages', adminController.getMessages);

module.exports = router;