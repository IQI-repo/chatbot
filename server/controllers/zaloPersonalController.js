const { chatWithOpenAI } = require('../ai/openai');
const axios = require('axios');

exports.gatewayWebhook = async (req, res) => {
  try {
    const userId  = req.body.from;
    const message = req.body.message;
    if (!userId || !message) return res.status(400).end();

    const reply = await chatWithOpenAI(message);

    await axios.post(`${process.env.GATEWAY_API_URL}/api/gateway/send-text`, {
      to: userId,
      message: reply
    });
    res.json({ ok: 1 });
  } catch (err) {
    res.status(500).end();
  }
};