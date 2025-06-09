const vision = require('@google-cloud/vision');

const client = new vision.ImageAnnotatorClient({
  apiKey: process.env.GEMINI_KEY
});

exports.analyzeImage = async (image_base64) => {
  const base64Data = image_base64.replace(/^data:image\/\w+;base64,/, "");
  const imgBuffer = Buffer.from(base64Data, 'base64');
  try {
    const [result] = await client.labelDetection({ image: { content: imgBuffer } });
    const labels = result.labelAnnotations.map(lbl => lbl.description).slice(0, 5);
    if (!labels.length) return "Không nhận diện được vật thể chính trong ảnh!";
    return `AI phát hiện các vật thể: ${labels.join(', ')}.`;
  } catch (err) {
    console.error("Lỗi Vision API:", err.message);
    return "Không thể nhận diện ảnh do lỗi AI!";
  }
};