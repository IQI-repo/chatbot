const mysql = require('mysql2/promise');
require('dotenv').config();

// Create a connection pool
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  port: process.env.DB_PORT || 3306,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Test the connection and count tables
const testConnection = async () => {
  try {
    const connection = await pool.getConnection();
    console.log('Successfully connected to MySQL database');
    
    // Count tables in the database
    const [rows] = await connection.query(
      'SELECT COUNT(*) as tableCount FROM information_schema.tables WHERE table_schema = ?', 
      [process.env.DB_NAME]
    );
    
    console.log(`Database ${process.env.DB_NAME} contains ${rows[0].tableCount} tables`);
    
    // Get list of tables
    const [tables] = await connection.query(
      'SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA = ? ORDER BY TABLE_NAME', 
      [process.env.DB_NAME]
    );
    
    if (tables.length > 0) {
      console.log('Tables in database:');
      tables.forEach((table, index) => {
        console.log(`${index + 1}. ${table.TABLE_NAME}`);
      });
    }
    
    connection.release();
    return true;
  } catch (error) {
    console.error('Error connecting to MySQL database:', error);
    return false;
  }
};

module.exports = {
  pool,
  testConnection
};
