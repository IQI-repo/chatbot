const { chatWithOpenAI } = require('../ai/openai');
const fs = require('fs').promises;
const path = require('path');

// Optional imports with error handling
let analyzeImage, createVoiceMp3, readMenuFile, searchTrainingData;
try {
  analyzeImage = require('../ai/vision').analyzeImage;
  createVoiceMp3 = require('../ai/tts').createVoiceMp3;
  const dataHelper = require('../utils/dataHelper');
  readMenuFile = dataHelper.readMenuFile;
  searchTrainingData = dataHelper.searchTrainingData;
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

    // Search training data for relevant information
    let searchResults = [];
    if (searchTrainingData) {
      try {
        searchResults = await searchTrainingData(message);
      } catch (err) {
        console.error('Training data search error:', err);
      }
    }
    
    // Format search results if any found
    let contextData = '';
    if (searchResults && searchResults.length > 0) {
      contextData = 'Dữ liệu tìm thấy:\n';
      
      // Group results by type
      const restaurants = searchResults.filter(r => r.type === 'restaurant');
      const items = searchResults.filter(r => r.type === 'item');
      
      if (restaurants.length > 0) {
        contextData += '\nNhà hàng:\n';
        restaurants.forEach(r => {
          contextData += `- ${r.name}\n  Địa chỉ: ${r.address || 'Không có thông tin'}\n`;
          if (r.time_open) {
            try {
              const timeData = JSON.parse(r.time_open);
              if (timeData.data && timeData.data.start && timeData.data.end) {
                contextData += `  Giờ mở cửa: ${timeData.data.start} - ${timeData.data.end}\n`;
              }
            } catch {}
          }
        });
      }
      
      if (items.length > 0) {
        contextData += '\nMón ăn/đồ uống:\n';
        items.forEach(item => {
          contextData += `- ${item.name} (${item.price.toLocaleString('vi-VN')}đ) tại ${item.restaurant}\n`;
        });
      }
    }
    
    const aiReply = await chatWithOpenAI(message, contextData);
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