const { chatWithOpenAI } = require('../ai/openai');
const axios = require('axios');

exports.handleWebhook = async (req, res) => {
  try {
    const { message, sender } = extractZaloMessage(req.body);
    if (message) {
      const reply = await chatWithOpenAI(message);
      await sendZaloMessage(sender, reply);
    }
    res.status(200).json({ code: 0 });
  } catch (e) {
    res.status(500).json({ code: 1 });
  }
};

function extractZaloMessage(body) {
  const user_id = body.sender.id;
  const msg = body.message && body.message.text;
  return { sender: user_id, message: msg };
}

async function sendZaloMessage(user_id, text) {
  const ZALO_OA_TOKEN = process.env.ZALO_OA_TOKEN;
  await axios.post(
    `https://openapi.zalo.me/v3.0/oa/message`, {
      recipient: { user_id },
      message: { text }
    },
    { headers: { access_token: ZALO_OA_TOKEN, 'Content-Type': 'application/json' } }
  );
}