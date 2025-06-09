const { chatWithOpenAI } = require('../ai/openai');
const axios = require('axios');

exports.verifyWebhook = (req, res) => {
  const VERIFY_TOKEN = process.env.FB_VERIFY_TOKEN || "bo_ship_verify";
  const mode = req.query['hub.mode'];
  const token = req.query['hub.verify_token'];
  const challenge = req.query['hub.challenge'];
  if (mode && token && mode === 'subscribe' && token === VERIFY_TOKEN) {
    res.status(200).send(challenge);
  } else {
    res.sendStatus(403);
  }
};

exports.handleWebhook = async (req, res) => {
  try {
    const body = req.body;
    if (body.object === 'page') {
      body.entry.forEach(async (entry) => {
        const event = entry.messaging[0];
        const sender_psid = event.sender.id;
        if (event.message && event.message.text) {
          const reply = await chatWithOpenAI(event.message.text);
          await sendMessageToFB(sender_psid, reply);
        }
      });
      res.status(200).send('EVENT_RECEIVED');
    } else {
      res.sendStatus(404);
    }
  } catch (err) {
    res.sendStatus(500);
  }
};

async function sendMessageToFB(sender_psid, text) {
  const PAGE_ACCESS_TOKEN = process.env.FB_PAGE_TOKEN;
  await axios.post(
    `https://graph.facebook.com/v18.0/me/messages?access_token=${PAGE_ACCESS_TOKEN}`,
    {
      recipient: { id: sender_psid },
      message: { text }
    }
  );
}