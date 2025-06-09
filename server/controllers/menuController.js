const path = require('path');
const fs = require('fs').promises;

const menuFile = path.join(__dirname, '../../data/menu.json');

exports.getMenu = async (req, res) => {
  try {
    const data = await fs.readFile(menuFile, "utf8");
    res.json(JSON.parse(data));
  } catch {
    res.json({});
  }
};

exports.saveMenu = async (req, res) => {
  try {
    let menuObj;
    try { menuObj = JSON.parse(req.body.menu); }
    catch { return res.status(400).json({ error: "JSON không hợp lệ!" }); }
    await fs.writeFile(menuFile, JSON.stringify(menuObj, null, 2));
    res.json({ ok: 1 });
  } catch {
    res.status(500).json({ error: "Không thể lưu menu!" });
  }
};