/**
 * Restaurant API Service
 * Handles interactions with the restaurant API
 */
const axios = require('axios');

/**
 * Check if a message is related to food or restaurants
 * @param {string} message - The user's message
 * @returns {boolean} - True if the message is food-related
 */
const isFoodRelatedQuery = (message) => {
  // Convert message to lowercase for case-insensitive matching
  const lowerMessage = message.toLowerCase();
  
  // List of food-related keywords in Vietnamese
  const foodKeywords = [
    'ăn', 'uống', 'đồ ăn', 'thức ăn', 'món ăn', 'nhà hàng', 'quán ăn', 
    'đặt món', 'đặt đồ', 'gọi đồ', 'đặt đồ ăn', 'đặt món ăn', 'trà sữa',
    'cà phê', 'cafe', 'coffee', 'trà', 'nước uống', 'đồ uống', 'thức uống',
    'đặt bàn', 'đặt chỗ', 'đói', 'khát', 'menu', 'thực đơn'
  ];
  
  // Check if any food keyword is present in the message
  return foodKeywords.some(keyword => lowerMessage.includes(keyword));
};

/**
 * Get restaurant information from the API
 * @param {string} query - The user's food-related query
 * @returns {Promise<Object>} - Restaurant data
 */
const getRestaurantInfo = async (query) => {
  try {
    const response = await axios.post('http://103.116.9.57:8000/api/restaurant-query', {
      question: query
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error fetching restaurant data:', error);
    throw new Error('Failed to get restaurant information');
  }
};

/**
 * Format restaurant data into a readable response
 * @param {Object} data - Restaurant API response data
 * @returns {string} - Formatted response
 */
const formatRestaurantResponse = (data) => {
  try {
    let response = '';
    
    // Add answer if available
    if (data.answer) {
      response += `${data.answer}\n\n`;
    }
    
    // Add top restaurants if available
    if (data.top_restaurants && data.top_restaurants.length > 0) {
      response += `**Nhà hàng đề xuất:**\n`;
      data.top_restaurants.forEach(restaurant => {
        response += `- ${restaurant}\n`;
      });
      response += '\n';
    }
    
    // Add menu items if available
    if (data.top_menu_items && data.top_menu_items.length > 0) {
      response += `**Món ăn đề xuất:**\n`;
      data.top_menu_items.forEach(item => {
        response += `- ${item}\n`;
      });
    }
    
    return response.trim();
  } catch (error) {
    console.error('Error formatting restaurant response:', error);
    return 'Có thông tin về nhà hàng nhưng không thể hiển thị chi tiết. Vui lòng thử lại.';
  }
};

module.exports = {
  isFoodRelatedQuery,
  getRestaurantInfo,
  formatRestaurantResponse
};
