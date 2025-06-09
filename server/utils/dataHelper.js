const fs = require('fs').promises;
const path = require('path');

exports.readMenuFile = async () => {
  try {
    const data = await fs.readFile(path.join(__dirname, '../../data/menu.json'), 'utf8');
    return JSON.parse(data);
  } catch (err) {
    return { notice: "Không tìm thấy file menu!" };
  }
}