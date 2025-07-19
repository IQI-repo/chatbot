const express = require('express');
const router = express.Router();
const fbCtrl = require('../controllers/fbController');

/**
 * @swagger
 * tags:
 *   name: Facebook
 *   description: Facebook Messenger webhook endpoints
 */

/**
 * @swagger
 * /fb/webhook:
 *   get:
 *     summary: Verify Facebook webhook
 *     description: Endpoint for Facebook webhook verification challenge
 *     tags: [Facebook]
 *     parameters:
 *       - in: query
 *         name: hub.mode
 *         schema:
 *           type: string
 *         required: true
 *         description: Mode of the webhook verification
 *       - in: query
 *         name: hub.verify_token
 *         schema:
 *           type: string
 *         required: true
 *         description: Verification token for the webhook
 *       - in: query
 *         name: hub.challenge
 *         schema:
 *           type: string
 *         required: true
 *         description: Challenge string to be echoed back
 *     responses:
 *       200:
 *         description: Challenge string returned for successful verification
 *         content:
 *           text/plain:
 *             schema:
 *               type: string
 *       403:
 *         description: Verification failed
 */
router.get('/webhook', fbCtrl.verifyWebhook);

/**
 * @swagger
 * /fb/webhook:
 *   post:
 *     summary: Handle Facebook webhook events
 *     description: Processes incoming messages and events from Facebook Messenger
 *     tags: [Facebook]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               object:
 *                 type: string
 *                 description: The object type (page)
 *               entry:
 *                 type: array
 *                 description: Array of entry objects
 *                 items:
 *                   type: object
 *                   properties:
 *                     id:
 *                       type: string
 *                     messaging:
 *                       type: array
 *                       items:
 *                         type: object
 *     responses:
 *       200:
 *         description: Event processed successfully
 */
router.post('/webhook', fbCtrl.handleWebhook);

module.exports = router;