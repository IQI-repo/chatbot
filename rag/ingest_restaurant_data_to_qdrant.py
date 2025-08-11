import os
import logging
import json
import mysql.connector
import numpy as np
from dotenv import load_dotenv
from src.embeddings_manager import EmbeddingsManager
from src.qdrant_manager import QdrantManager
from qdrant_client.http import models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Database connection configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_DB_HOST'),
    'port': int(os.getenv('MYSQL_DB_PORT', 3306)),
    'user': os.getenv('MYSQL_DB_USERNAME'),
    'password': os.getenv('MYSQL_DB_PASSWORD'),
    'database': os.getenv('MYSQL_DB_NAME', 'boship')  # Default database name
}

def get_db_connection():
    """
    Establish a connection to the MySQL database
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.info("Database connection established successfully")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        raise

def fetch_restaurant_data():
    """
    Fetch restaurant data and related information from MySQL database
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch restaurants
        logging.info("Fetching restaurants from database...")
        cursor.execute("""
            SELECT * FROM restaurants
            WHERE is_active = 1
        """)
        restaurants = cursor.fetchall()
        logging.info(f"Fetched {len(restaurants)} restaurants")
        
        # Process each restaurant to get menu items
        for restaurant in restaurants:
            restaurant_id = restaurant['id']
            
            # Fetch menu items for this restaurant
            cursor.execute("""
                SELECT i.*, ic.name as category_name
                FROM items i
                LEFT JOIN item_category ic ON i.item_category_id = ic.id
                WHERE i.restaurant_id = %s AND i.is_active = 1
            """, (restaurant_id,))
            restaurant['items'] = cursor.fetchall()
            
        return restaurants
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching restaurant data: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def create_text_representations(restaurants):
    """
    Create text representations for restaurants to generate embeddings
    """
    restaurant_texts = []
    
    for restaurant in restaurants:
        # Basic restaurant info
        restaurant_text = f"Restaurant ID: {restaurant.get('id')}\n"
        restaurant_text += f"Name: {restaurant.get('name', 'Unknown')}\n"
        restaurant_text += f"Address: {restaurant.get('address', 'Unknown')}\n"
        restaurant_text += f"Location: Latitude {restaurant.get('latitude', 'Unknown')}, Longitude {restaurant.get('longitude', 'Unknown')}\n"
        restaurant_text += f"Rating: {restaurant.get('rating', 0)}\n"
        
        if restaurant.get('address_description'):
            restaurant_text += f"Address Description: {restaurant.get('address_description')}\n"
        
        if restaurant.get('phone'):
            restaurant_text += f"Phone: {restaurant.get('phone')}\n"
        
        if restaurant.get('categories'):
            restaurant_text += f"Categories: {restaurant.get('categories')}\n"
        
        # Menu items
        if restaurant.get('items'):
            restaurant_text += "Menu Items:\n"
            for item in restaurant.get('items', []):
                restaurant_text += f"- {item.get('name', 'Unknown')}\n"
                restaurant_text += f"  Price: {item.get('price', 0)} VND"
                if item.get('old_price') and item.get('old_price') > item.get('price', 0):
                    restaurant_text += f", Original Price: {item.get('old_price')} VND\n"
                else:
                    restaurant_text += "\n"
                    
                if item.get('category_name'):
                    restaurant_text += f"  Category: {item.get('category_name')}\n"
                
                if item.get('description'):
                    restaurant_text += f"  Description: {item.get('description')}\n"
                
                if item.get('is_recommended'):
                    restaurant_text += f"  Recommended Item\n"
                
                if item.get('is_popular'):
                    restaurant_text += f"  Popular Item\n"
        
        restaurant_texts.append(restaurant_text)
    
    return restaurant_texts

def ingest_restaurant_data_to_qdrant():
    """
    Main function to ingest restaurant data from MySQL to Qdrant
    """
    load_dotenv()
    
    # Check for required API key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    if not openai_api_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    if not qdrant_api_key:
        logging.warning("QDRANT_API_KEY not found in environment variables, using in-memory storage")
    
    try:
        # Initialize components
        logging.info("Initializing components...")
        embeddings_manager = EmbeddingsManager(openai_api_key)
        qdrant_manager = QdrantManager()  # Use the existing QdrantManager for restaurants
        
        # Fetch restaurant data from MySQL
        logging.info("Fetching restaurant data from MySQL...")
        restaurants_data = fetch_restaurant_data()
        
        if not restaurants_data:
            logging.error("No restaurant data loaded! Check database connection and queries.")
            return False
        
        # Create text representations for restaurants
        logging.info("Creating text representations...")
        restaurant_texts = create_text_representations(restaurants_data)
        
        # Generate embeddings
        logging.info("Generating embeddings...")
        restaurant_embeddings = embeddings_manager.create_embeddings(restaurant_texts)
        logging.info(f"Generated {len(restaurant_embeddings)} embeddings")
        
        # Ingest data into Qdrant
        logging.info("Ingesting restaurant data into Qdrant...")
        success = qdrant_manager.ingest_data(restaurants_data, restaurant_embeddings)
        
        if success:
            logging.info("Restaurant data ingestion completed successfully!")
            return True
        else:
            logging.error("Restaurant data ingestion failed!")
            return False
            
    except Exception as e:
        logging.error(f"Error during restaurant data ingestion: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    ingest_restaurant_data_to_qdrant()
