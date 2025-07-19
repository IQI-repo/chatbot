const express = require('express');
const router = express.Router();
const menuController = require('../controllers/menuController');

/**
 * @swagger
 * tags:
 *   name: Menu
 *   description: Restaurant menu operations
 */

/**
 * @swagger
 * components:
 *   schemas:
 *     Menu:
 *       type: object
 *       properties:
 *         name:
 *           type: string
 *           description: Restaurant name
 *         hours:
 *           type: object
 *           properties:
 *             open:
 *               type: string
 *               description: Opening time
 *             close:
 *               type: string
 *               description: Closing time
 *         items:
 *           type: array
 *           items:
 *             type: object
 *             properties:
 *               name:
 *                 type: string
 *                 description: Item name
 *               price:
 *                 type: number
 *                 description: Item price
 *               category:
 *                 type: string
 *                 description: Item category
 */

/**
 * @swagger
 * /menu:
 *   get:
 *     summary: Get restaurant menu
 *     description: Retrieves the restaurant menu and operating hours
 *     tags: [Menu]
 *     responses:
 *       200:
 *         description: Menu retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Menu'
 *       500:
 *         description: Server error
 */
router.get('/', menuController.getMenu);

/**
 * @swagger
 * /menu:
 *   post:
 *     summary: Save restaurant menu
 *     description: Updates the restaurant menu and operating hours
 *     tags: [Menu]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/Menu'
 *     responses:
 *       200:
 *         description: Menu saved successfully
 *       500:
 *         description: Server error
 */
router.post('/', menuController.saveMenu);

module.exports = router;