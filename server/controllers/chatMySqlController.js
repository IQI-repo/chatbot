const { pool } = require('../utils/db');
const { chatWithOpenAI } = require('../ai/openai');
const { isFoodRelatedQuery, getRestaurantInfo, formatRestaurantResponse } = require('../utils/restaurantApi');

// Optional imports with error handling
let analyzeImage, createVoiceMp3;
try {
  analyzeImage = require('../ai/vision').analyzeImage;
  createVoiceMp3 = require('../ai/tts').createVoiceMp3;
} catch (err) {
  console.log('Some AI services are not available:', err.message);
}

/**
 * Get all chat sessions for a user
 */
exports.getUserChatSessions = async (req, res) => {
  try {
    const { user_id } = req.params;
    
    const [sessions] = await pool.query(
      `SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY started_at DESC`,
      [user_id]
    );
    
    return res.json({ success: true, sessions });
  } catch (error) {
    console.error('Error fetching chat sessions:', error);
    return res.status(500).json({ success: false, error: 'Failed to fetch chat sessions' });
  }
};

/**
 * Create a new chat session
 */
exports.createChatSession = async (req, res) => {
  try {
    const { user_id, context, bot_model } = req.body;
    
    // Log the request body for debugging
    console.log('Create session request body:', req.body);
    
    if (!user_id) {
      return res.status(400).json({ success: false, error: 'User ID is required' });
    }
    
    // Validate user_id is a number
    const userId = parseInt(user_id);
    if (isNaN(userId)) {
      return res.status(400).json({ success: false, error: 'Invalid user ID format' });
    }
    
    // Check if user exists
    const [users] = await pool.query('SELECT id FROM users WHERE id = ?', [userId]);
    if (users.length === 0) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }
    
    const [result] = await pool.query(
      `INSERT INTO chat_sessions (user_id, started_at, context, bot_model) 
       VALUES (?, NOW(), ?, ?)`,
      [userId, context || null, bot_model || null]
    );
    
    const session_id = result.insertId;
    
    return res.json({ 
      success: true, 
      session: { 
        id: session_id,
        user_id: userId,
        started_at: new Date(),
        context: context || null,
        bot_model: bot_model || null
      } 
    });
  } catch (error) {
    console.error('Error creating chat session:', error);
    return res.status(500).json({ success: false, error: 'Failed to create chat session' });
  }
};

/**
 * End a chat session
 */
exports.endChatSession = async (req, res) => {
  try {
    const { session_id } = req.params;
    
    const [result] = await pool.query(
      `UPDATE chat_sessions SET ended_at = NOW() WHERE id = ?`,
      [session_id]
    );
    
    if (result.affectedRows === 0) {
      return res.status(404).json({ success: false, error: 'Chat session not found' });
    }
    
    return res.json({ success: true, message: 'Chat session ended' });
  } catch (error) {
    console.error('Error ending chat session:', error);
    return res.status(500).json({ success: false, error: 'Failed to end chat session' });
  }
};

/**
 * Get messages for a specific chat session
 */
exports.getChatMessages = async (req, res) => {
  try {
    const { session_id } = req.params;
    
    const [messages] = await pool.query(
      `SELECT * FROM chat_messages WHERE session_id = ? ORDER BY sent_at ASC`,
      [session_id]
    );
    
    return res.json({ success: true, messages });
  } catch (error) {
    console.error('Error fetching chat messages:', error);
    return res.status(500).json({ success: false, error: 'Failed to fetch chat messages' });
  }
};

/**
 * Send a new message in a chat session
 */
exports.sendChatMessage = async (req, res) => {
  try {
    const { session_id, sender, message, metadata } = req.body;
    
    if (!session_id || !message) {
      return res.status(400).json({ 
        success: false, 
        error: 'Session ID and message are required' 
      });
    }
    
    // Check if session exists
    const [sessionCheck] = await pool.query(
      `SELECT * FROM chat_sessions WHERE id = ?`,
      [session_id]
    );
    
    if (sessionCheck.length === 0) {
      return res.status(404).json({ success: false, error: 'Chat session not found' });
    }
    
    // Insert the message
    const [result] = await pool.query(
      `INSERT INTO chat_messages (session_id, sender, message, sent_at, metadata) 
       VALUES (?, ?, ?, NOW(), ?)`,
      [session_id, sender || 'user', message, metadata ? JSON.stringify(metadata) : null]
    );
    
    const message_id = result.insertId;
    
    // If this is a user message, generate a bot response
    if (sender === 'user' || !sender) {
      try {
        console.log('Processing message with AI:', message);
        
        // Check if the message is food-related
        let aiReply;
        let contextData = '';
        
        if (isFoodRelatedQuery(message)) {
          try {
            console.log('Food-related query detected, calling restaurant API');
            const restaurantData = await getRestaurantInfo(message);
            
            // Format the restaurant data into a readable response
            const formattedResponse = formatRestaurantResponse(restaurantData);
            
            // Use the formatted response as context for the AI
            contextData = formattedResponse;
            console.log('Restaurant API response:', formattedResponse);
          } catch (restaurantError) {
            console.error('Error getting restaurant information:', restaurantError);
            // Continue with normal AI processing if restaurant API fails
          }
        }
        
        // Process with AI and get response
        if (chatWithOpenAI) {
          aiReply = await chatWithOpenAI(message, contextData);
        } else {
          aiReply = "I'm sorry, the AI service is currently unavailable.";
          console.error('chatWithOpenAI function is not available');
        }
        
        console.log('AI reply generated:', aiReply);
        
        // Save the bot's response
        await pool.query(
          `INSERT INTO chat_messages (session_id, sender, message, sent_at) 
           VALUES (?, ?, ?, NOW())`,
          [session_id, 'bot', aiReply]
        );
        
        return res.json({ 
          success: true, 
          message: { id: message_id, session_id, sender, message, sent_at: new Date() },
          reply: { sender: 'bot', message: aiReply, sent_at: new Date() }
        });
      } catch (aiError) {
        console.error('Error generating AI response:', aiError);
        // Still return success for the user message, but include the error
        return res.json({ 
          success: true, 
          message: { id: message_id, session_id, sender, message, sent_at: new Date() },
          error: 'Failed to generate AI response'
        });
      }
    }
    
    return res.json({ 
      success: true, 
      message: { id: message_id, session_id, sender, message, sent_at: new Date() }
    });
  } catch (error) {
    console.error('Error sending chat message:', error);
    return res.status(500).json({ success: false, error: 'Failed to send chat message' });
  }
};

/**
 * Get user information
 */
exports.getUserInfo = async (req, res) => {
  try {
    const { user_id } = req.params;
    
    const [users] = await pool.query(
      `SELECT id, name, email, avatar, avatar_display FROM users WHERE id = ?`,
      [user_id]
    );
    
    if (users.length === 0) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }
    
    return res.json({ success: true, user: users[0] });
  } catch (error) {
    console.error('Error fetching user info:', error);
    return res.status(500).json({ success: false, error: 'Failed to fetch user info' });
  }
};

/**
 * Get chat statistics
 */
exports.getChatStats = async (req, res) => {
  try {
    // Get total sessions
    const [sessionCount] = await pool.query(
      `SELECT COUNT(*) as count FROM chat_sessions`
    );
    
    // Get total messages
    const [messageCount] = await pool.query(
      `SELECT COUNT(*) as count FROM chat_messages`
    );
    
    // Get total users
    const [userCount] = await pool.query(
      `SELECT COUNT(*) as count FROM users`
    );
    
    // Get average messages per session
    const [avgMessages] = await pool.query(
      `SELECT AVG(message_count) as average FROM (
         SELECT session_id, COUNT(*) as message_count 
         FROM chat_messages 
         GROUP BY session_id
       ) as message_counts`
    );
    
    // Get most active user
    const [activeUser] = await pool.query(
      `SELECT u.name, COUNT(cs.id) as session_count 
       FROM users u 
       JOIN chat_sessions cs ON u.id = cs.user_id 
       GROUP BY u.id 
       ORDER BY session_count DESC 
       LIMIT 1`
    );
    
    return res.json({
      success: true,
      stats: {
        totalSessions: sessionCount[0].count,
        totalMessages: messageCount[0].count,
        totalUsers: userCount[0].count,
        avgMessagesPerSession: avgMessages[0].average || 0,
        mostActiveUser: activeUser[0] || null
      }
    });
  } catch (error) {
    console.error('Error fetching chat stats:', error);
    return res.status(500).json({ success: false, error: 'Failed to fetch chat statistics' });
  }
};

/**
 * Delete a chat session and its messages
 */
exports.deleteChatSession = async (req, res) => {
  try {
    const { session_id } = req.params;
    
    // Start a transaction to ensure data consistency
    const connection = await pool.getConnection();
    await connection.beginTransaction();
    
    try {
      // First delete all messages in the session
      await connection.query(
        `DELETE FROM chat_messages WHERE session_id = ?`,
        [session_id]
      );
      
      // Then delete the session itself
      const [result] = await connection.query(
        `DELETE FROM chat_sessions WHERE id = ?`,
        [session_id]
      );
      
      // Commit the transaction
      await connection.commit();
      connection.release();
      
      if (result.affectedRows === 0) {
        return res.status(404).json({ success: false, error: 'Chat session not found' });
      }
      
      return res.json({ success: true, message: 'Chat session deleted successfully' });
    } catch (error) {
      // Rollback in case of error
      await connection.rollback();
      connection.release();
      throw error;
    }
  } catch (error) {
    console.error('Error deleting chat session:', error);
    return res.status(500).json({ success: false, error: 'Failed to delete chat session' });
  }
};
