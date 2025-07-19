const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chatController');

/**
 * @swagger
 * /chat:
 *   post:
 *     summary: Process user chat messages
 *     description: Handles user chat messages and returns AI responses
 *     tags: [Chat]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - message
 *             properties:
 *               message:
 *                 type: string
 *                 description: User's chat message
 *               channel:
 *                 type: string
 *                 description: Communication channel (optional)
 *               image_base64:
 *                 type: string
 *                 description: Base64 encoded image for analysis (optional)
 *     responses:
 *       200:
 *         description: Successful response
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 reply:
 *                   type: string
 *                   description: AI response to the user's message
 *                 voice_url:
 *                   type: string
 *                   description: URL to voice audio of the response (if available)
 *       500:
 *         description: Server error
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 reply:
 *                   type: string
 *                   description: Error message
 */
router.post('/', chatController.userChat);

module.exports = router;