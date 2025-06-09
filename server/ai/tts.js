const textToSpeech = require('@google-cloud/text-to-speech');
const fs = require('fs').promises;
const path = require('path');

const ttsClient = new textToSpeech.TextToSpeechClient({
  apiKey: process.env.GEMINI_KEY
});

exports.createVoiceMp3 = async (text, fileNameHint = 'reply') => {
  const request = {
    input: { text },
    voice: { languageCode: 'vi-VN', ssmlGender: 'FEMALE' },
    audioConfig: { audioEncoding: 'MP3' },
  };

  const [response] = await ttsClient.synthesizeSpeech(request);
  const safeName = `${fileNameHint}_${Date.now()}.mp3`;
  const outPath = path.join(__dirname, '../../data/', safeName);
  await fs.writeFile(outPath, response.audioContent, 'binary');
  return '/data/' + safeName;
};