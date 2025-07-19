const express = require('express');
const router = express.Router();
const chatMySqlController = require('../controllers/chatMySqlController');

/**
 * @swagger
 * tags:
 *   name: Chat MySQL
 *   description: Chat operations using MySQL database
 */

/**
 * @swagger
 * components:
 *   schemas:
 *     ChatSession:
 *       type: object
 *       required:
 *         - user_id
 *       properties:
 *         id:
 *           type: integer
 *           description: The auto-generated id of the chat session
 *         user_id:
 *           type: string
 *           description: User identifier
 *         started_at:
 *           type: string
 *           format: date-time
 *           description: Session start timestamp
 *         ended_at:
 *           type: string
 *           format: date-time
 *           description: Session end timestamp
 *     ChatMessage:
 *       type: object
 *       required:
 *         - session_id
 *         - content
 *         - role
 *       properties:
 *         id:
 *           type: integer
 *           description: The auto-generated id of the message
 *         session_id:
 *           type: integer
 *           description: Chat session ID
 *         content:
 *           type: string
 *           description: Message content
 *         role:
 *           type: string
 *           enum: [user, assistant]
 *           description: Message sender role
 *         timestamp:
 *           type: string
 *           format: date-time
 *           description: Message timestamp
 */

/**
 * @swagger
 * /chat-mysql/sessions/user/{user_id}:
 *   get:
 *     summary: Get all chat sessions for a user
 *     tags: [Chat MySQL]
 *     parameters:
 *       - in: path
 *         name: user_id
 *         schema:
 *           type: string
 *         required: true
 *         description: User ID
 *     responses:
 *       200:
 *         description: List of chat sessions
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/ChatSession'
 */
router.get('/sessions/user/:user_id', chatMySqlController.getUserChatSessions);

/**
 * @swagger
 * /chat-mysql/sessions:
 *   post:
 *     summary: Create a new chat session
 *     tags: [Chat MySQL]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - user_id
 *             properties:
 *               user_id:
 *                 type: string
 *     responses:
 *       201:
 *         description: Created chat session
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ChatSession'
 */
router.post('/sessions', chatMySqlController.createChatSession);

/**
 * @swagger
 * /chat-mysql/sessions/{session_id}/end:
 *   put:
 *     summary: End a chat session
 *     tags: [Chat MySQL]
 *     parameters:
 *       - in: path
 *         name: session_id
 *         schema:
 *           type: integer
 *         required: true
 *         description: Chat session ID
 *     responses:
 *       200:
 *         description: Session ended successfully
 */
router.put('/sessions/:session_id/end', chatMySqlController.endChatSession);

/**
 * @swagger
 * /chat-mysql/sessions/{session_id}:
 *   delete:
 *     summary: Delete a chat session
 *     tags: [Chat MySQL]
 *     parameters:
 *       - in: path
 *         name: session_id
 *         schema:
 *           type: integer
 *         required: true
 *         description: Chat session ID
 *     responses:
 *       200:
 *         description: Session deleted successfully
 */
router.delete('/sessions/:session_id', chatMySqlController.deleteChatSession);

/**
 * @swagger
 * /chat-mysql/messages/{session_id}:
 *   get:
 *     summary: Get all messages for a chat session
 *     tags: [Chat MySQL]
 *     parameters:
 *       - in: path
 *         name: session_id
 *         schema:
 *           type: integer
 *         required: true
 *         description: Chat session ID
 *     responses:
 *       200:
 *         description: List of chat messages
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/ChatMessage'
 */
router.get('/messages/:session_id', chatMySqlController.getChatMessages);

/**
 * @swagger
 * /chat-mysql/messages:
 *   post:
 *     summary: Send a new chat message
 *     tags: [Chat MySQL]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - session_id
 *               - content
 *               - role
 *             properties:
 *               session_id:
 *                 type: integer
 *               content:
 *                 type: string
 *               role:
 *                 type: string
 *                 enum: [user, assistant]
 *     responses:
 *       201:
 *         description: Message sent successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ChatMessage'
 */
router.post('/messages', chatMySqlController.sendChatMessage);

/**
 * @swagger
 * /chat-mysql/users/{user_id}:
 *   get:
 *     summary: Get user information
 *     tags: [Chat MySQL]
 *     parameters:
 *       - in: path
 *         name: user_id
 *         schema:
 *           type: string
 *         required: true
 *         description: User ID
 *     responses:
 *       200:
 *         description: User information
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 id:
 *                   type: string
 *                 name:
 *                   type: string
 *                 email:
 *                   type: string
 */
router.get('/users/:user_id', chatMySqlController.getUserInfo);

/**
 * @swagger
 * /chat-mysql/stats:
 *   get:
 *     summary: Get chat statistics
 *     tags: [Chat MySQL]
 *     responses:
 *       200:
 *         description: Chat statistics
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 total_sessions:
 *                   type: integer
 *                 total_messages:
 *                   type: integer
 *                 active_users:
 *                   type: integer
 */
router.get('/stats', chatMySqlController.getChatStats);

module.exports = router;
