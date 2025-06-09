const { chatWithOpenAI } = require('../ai/openai');
const fs = require('fs').promises;
const path = require('path');

// Optional imports with error handling
let analyzeImage, createVoiceMp3, readMenuFile;
try {
  analyzeImage = require('../ai/vision').analyzeImage;
  createVoiceMp3 = require('../ai/tts').createVoiceMp3;
  readMenuFile = require('../utils/dataHelper').readMenuFile;
} catch (err) {
  console.log('Some services are not available:', err.message);
}

exports.userChat = async (req, res) => {
  try {
    const { message, channel, image_base64 } = req.body;

    if (image_base64 && analyzeImage) {
      try {
        const analyzeResult = await analyzeImage(image_base64);
        let voice_url = null;
        try {
          if (createVoiceMp3) {
            voice_url = await createVoiceMp3(analyzeResult, 'img_reply');
          }
        } catch {}
        return res.json({ reply: analyzeResult, voice_url });
      } catch (err) {
        console.error('Image analysis error:', err);
        return res.json({ reply: "Xin lỗi, tôi không thể phân tích hình ảnh lúc này." });
      }
    }

    if (message && readMenuFile && (message.toLowerCase().includes('menu') || message.toLowerCase().includes('giờ'))) {
      try {
        const menuData = await readMenuFile();
        return res.json({ reply: `Menu/giờ mở cửa:\n${JSON.stringify(menuData, null, 2)}`});
      } catch (err) {
        console.error('Menu reading error:', err);
      }
    }

    const aiReply = await chatWithOpenAI(message);
    let voice_url = null;
    try {
      if (createVoiceMp3) {
        voice_url = await createVoiceMp3(aiReply, 'reply');
      }
    } catch {}

    // Log chat
    try {
      const logPath = path.join(__dirname, '../../data/logs.json');
      let logs = [];
      try {
        const raw = await fs.readFile(logPath, 'utf8');
        logs = JSON.parse(raw);
      } catch {}
      logs.push({from: 'user', content: message, time: new Date().toLocaleString()});
      logs.push({from: 'bot', content: aiReply, time: new Date().toLocaleString()});
      if (logs.length > 1000) logs = logs.slice(logs.length - 1000);
      await fs.writeFile(logPath, JSON.stringify(logs, null, 2));
    } catch (err) {
      console.error('Logging error:', err);
    }

    return res.json({ reply: aiReply, voice_url });
  } catch (err) {
    console.error('Chat error:', err);
    return res.status(500).json({ reply: 'Xin lỗi, có lỗi xảy ra!' });
  }
};