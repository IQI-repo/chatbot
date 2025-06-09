const path = require('path');
const fs = require('fs').promises;

exports.getMessages = async (req, res) => {
  try {
    const dataPath = path.join(__dirname, '../../data/logs.json');
    let data = [];
    try {
      const raw = await fs.readFile(dataPath, "utf8");
      data = JSON.parse(raw);
    } catch {}
    res.json({ messages: data });
  } catch (err) {
    res.json({ messages: [] });
  }
}