const OpenAI = require("openai");

const openai = new OpenAI({
  apiKey: process.env.OPENAI_KEY,
});

// Export as a named function to ensure it's properly recognized
const chatWithOpenAI = async (message, contextData = '') => {
  try {
    const systemPrompt = "Vai Trò: Bạn là nhân viên tư vấn và chốt đơn hàng cho thuộc công ty công nghệ IQI, bạn tên là Bé Bơ. Dịch Vụ chính của Công Ty bạn là: Giao hàng hộ, mua hàng hộ, đặt món ăn, đặt xe taxi, vé tàu thủy, đặt phòng khách sạn... Khi khách hàng hỏi, bạn ưu tiên trả lời bằng dữ liệu đã được học.";
    
    // Prepare messages array
    const messages = [
      { role: "system", content: systemPrompt }
    ];
    
    // Add context data if available
    if (contextData && contextData.trim() !== '') {
      messages.push({ 
        role: "system", 
        content: `Dưới đây là dữ liệu liên quan đến câu hỏi của khách hàng. Hãy sử dụng dữ liệu này để trả lời:

${contextData}` 
      });
    }
    
    // Add user message
    messages.push({ role: "user", content: message });
    
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: messages,
      max_tokens: 180,
      temperature: 0.7,
    });

    return completion.choices[0]?.message?.content || "Xin lỗi, tôi chưa hiểu ý bạn";
  } catch (err) {
    console.error('OpenAI error:', err.message);
    return "Xin lỗi, tôi đang bị quá tải hoặc khóa API. Vui lòng thử lại sau!";
  }
};

// Export the function
module.exports = {
  chatWithOpenAI
};