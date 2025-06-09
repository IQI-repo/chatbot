const OpenAI = require("openai");

const openai = new OpenAI({
  apiKey: process.env.OPENAI_KEY,
});

exports.chatWithOpenAI = async (message) => {
  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [{ role: "user", content: message }],
      max_tokens: 180,
      temperature: 0.7,
    });

    return completion.choices[0]?.message?.content || "Xin lỗi, tôi chưa hiểu ý bạn";
  } catch (err) {
    console.error('OpenAI error:', err.message);
    return "Xin lỗi, tôi đang bị quá tải hoặc khóa API. Vui lòng thử lại sau!";
  }
};