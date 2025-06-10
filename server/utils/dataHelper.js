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

exports.searchTrainingData = async (query) => {
  try {
    // Read the training data file
    const data = await fs.readFile(path.join(__dirname, '../training/data.json'), 'utf8');
    const jsonData = JSON.parse(data);
    
    // Normalize the query (lowercase, remove accents for better matching)
    const normalizedQuery = query.toLowerCase();
    
    // Search for restaurants and items matching the query
    const results = [];
    
    // Search through restaurants
    for (const restaurant of jsonData) {
      // Check if restaurant name matches
      if (restaurant.name && restaurant.name.toLowerCase().includes(normalizedQuery)) {
        results.push({
          type: 'restaurant',
          name: restaurant.name,
          address: restaurant.address || '',
          time_open: restaurant.time_open || ''
        });
      }
      
      // Check if any menu items match
      if (restaurant.items && Array.isArray(restaurant.items)) {
        const matchingItems = restaurant.items.filter(item => 
          item.name && item.name.toLowerCase().includes(normalizedQuery)
        ).map(item => ({
          type: 'item',
          name: item.name,
          price: item.price,
          restaurant: restaurant.name
        }));
        
        results.push(...matchingItems);
      }
    }
    
    return results;
  } catch (err) {
    console.error('Error searching training data:', err);
    return [];
  }
}