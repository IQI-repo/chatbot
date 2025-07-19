const express = require('express');
const router = express.Router();
const zaloPController = require('../controllers/zaloPersonalController');

/**
 * @swagger
 * tags:
 *   name: Zalo Personal
 *   description: Zalo Personal webhook endpoints
 */

/**
 * @swagger
 * /zalo-personal/webhook:
 *   post:
 *     summary: Handle Zalo Personal webhook events
 *     description: Processes incoming messages and events from Zalo Personal accounts
 *     tags: [Zalo Personal]
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
 *                 description: Type of event
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
router.post('/webhook', zaloPController.gatewayWebhook);

module.exports = router;