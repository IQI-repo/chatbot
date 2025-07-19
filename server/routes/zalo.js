const express = require('express');
const router = express.Router();
const zaloCtrl = require('../controllers/zaloController');

/**
 * @swagger
 * tags:
 *   name: Zalo
 *   description: Zalo OA webhook endpoints
 */

/**
 * @swagger
 * /zalo/webhook:
 *   post:
 *     summary: Handle Zalo webhook events
 *     description: Processes incoming messages and events from Zalo Official Account
 *     tags: [Zalo]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               app_id:
 *                 type: string
 *                 description: Zalo application ID
 *               event_name:
 *                 type: string
 *                 description: Type of event (user_send_text, user_send_image, etc.)
 *               sender:
 *                 type: object
 *                 properties:
 *                   id:
 *                     type: string
 *                     description: Sender ID
 *               message:
 *                 type: object
 *                 description: Message content
 *     responses:
 *       200:
 *         description: Event processed successfully
 */
router.post('/webhook', zaloCtrl.handleWebhook);

module.exports = router;