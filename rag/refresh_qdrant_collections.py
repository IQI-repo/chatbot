#!/usr/bin/env python3
"""
Script to refresh Qdrant collections with latest data from MySQL database.
This script can be scheduled with cron to run daily.

Example cron entry (runs at 3 AM every day):
0 3 * * * cd /path/to/chatbot/rag && python refresh_qdrant_collections.py >> /path/to/logs/qdrant_refresh.log 2>&1
"""

import os
import logging
import time
from datetime import datetime
import mysql.connector
import numpy as np
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from src.embeddings_manager import EmbeddingsManager

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

# Qdrant configuration
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
QDRANT_URL = "https://16f1329c-7600-4be6-8dc1-376daff8d555.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_PORT = 6333
EMBEDDING_SIZE = 1536  # OpenAI Ada embedding size

# Collection names
RESTAURANT_COLLECTION = "restaurant_collection"
HOTEL_COLLECTION = "hotel_collection"

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

def get_qdrant_client():
    """
    Initialize and return a Qdrant client
    """
    try:
        if QDRANT_API_KEY:
            client = QdrantClient(
                api_key=QDRANT_API_KEY,
                url=QDRANT_URL,
                port=QDRANT_PORT
            )
            logging.info("Connected to Qdrant cloud service")
        else:
            client = QdrantClient(":memory:")  # In-memory storage for testing
            logging.info("Using in-memory Qdrant instance (no API key provided)")
        
        return client
    except Exception as e:
        logging.error(f"Error initializing Qdrant client: {e}")
        raise

def create_collection(client, collection_name):
    """
    Create a new collection in Qdrant
    """
    try:
        logging.info(f"Creating collection '{collection_name}'")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_SIZE,
                distance=Distance.COSINE
            ),
            # Create payload indexes for faster filtering
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=0  # Index all vectors
            )
        )
        logging.info(f"Collection '{collection_name}' created successfully")
    except Exception as e:
        logging.error(f"Error creating collection '{collection_name}': {e}")
        raise

def delete_collection(client, collection_name):
    """
    Delete a collection from Qdrant if it exists
    """
    try:
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if collection_name in collection_names:
            logging.info(f"Deleting collection '{collection_name}'")
            client.delete_collection(collection_name=collection_name)
            logging.info(f"Collection '{collection_name}' deleted successfully")
        else:
            logging.info(f"Collection '{collection_name}' does not exist, nothing to delete")
    except Exception as e:
        logging.error(f"Error deleting collection '{collection_name}': {e}")
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

def fetch_hotel_data():
    """
    Fetch hotel data and related information from MySQL database
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch hotels
        logging.info("Fetching hotels from database...")
        cursor.execute("""
            SELECT * FROM hotels
            WHERE is_active = 1
        """)
        hotels = cursor.fetchall()
        logging.info(f"Fetched {len(hotels)} hotels")
        
        # Process each hotel to get rooms, amenities, and images
        for hotel in hotels:
            hotel_id = hotel['id']
            
            # Fetch rooms for this hotel
            cursor.execute("""
                SELECT * FROM hotel_rooms
                WHERE hotel_id = %s AND is_active = 1
            """, (hotel_id,))
            hotel['rooms'] = cursor.fetchall()
            
            # Fetch amenities for this hotel
            cursor.execute("""
                SELECT ham.hotel_id, ham.amenities_id, ha.name, hag.name as group_name
                FROM hotel_amenities_many ham
                JOIN hotel_amenities ha ON ham.amenities_id = ha.id
                LEFT JOIN hotel_amenities_group hag ON ha.group_id = hag.id
                WHERE ham.hotel_id = %s
            """, (hotel_id,))
            hotel['amenities'] = cursor.fetchall()
            
            # Fetch images for this hotel
            cursor.execute("""
                SELECT * FROM hotel_images
                WHERE hotel_id = %s
            """, (hotel_id,))
            hotel['images'] = cursor.fetchall()
            
        return hotels
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching hotel data: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def create_restaurant_text_representations(restaurants):
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

def create_hotel_text_representations(hotels):
    """
    Create text representations for hotels to generate embeddings
    """
    hotel_texts = []
    
    for hotel in hotels:
        # Basic hotel info
        hotel_text = f"Hotel ID: {hotel.get('id')}\n"
        hotel_text += f"Name: {hotel.get('name', 'Unknown')}\n"
        hotel_text += f"Address: {hotel.get('address', 'Unknown')}\n"
        hotel_text += f"Location: Latitude {hotel.get('latitude', 'Unknown')}, Longitude {hotel.get('longitude', 'Unknown')}\n"
        hotel_text += f"Rating: {hotel.get('rating', 0)}\n"
        
        if hotel.get('description'):
            hotel_text += f"Description: {hotel.get('description')}\n"
        
        if hotel.get('phone'):
            hotel_text += f"Phone: {hotel.get('phone')}\n"
        
        # Amenities
        if hotel.get('amenities'):
            hotel_text += "Amenities:\n"
            amenities_seen = set()
            for amenity in hotel.get('amenities', []):
                amenity_name = amenity.get('name', '')
                if amenity_name and amenity_name not in amenities_seen:
                    amenities_seen.add(amenity_name)
                    hotel_text += f"- {amenity_name}\n"
        
        # Rooms
        if hotel.get('rooms'):
            hotel_text += "Rooms:\n"
            for room in hotel.get('rooms', []):
                hotel_text += f"- {room.get('name', 'Unknown')}\n"
                hotel_text += f"  Price: {room.get('price', 0)} VND\n"
                
                if room.get('description'):
                    hotel_text += f"  Description: {room.get('description')}\n"
                
                if room.get('max_adults'):
                    hotel_text += f"  Max Adults: {room.get('max_adults')}\n"
                
                if room.get('max_children'):
                    hotel_text += f"  Max Children: {room.get('max_children')}\n"
        
        hotel_texts.append(hotel_text)
    
    return hotel_texts

def ingest_data_to_qdrant(client, collection_name, data, embeddings):
    """
    Ingest data and embeddings into Qdrant
    """
    try:
        logging.info(f"Ingesting {len(data)} items into '{collection_name}'")
        
        # Prepare points for batch upload
        points = []
        for i, (item, embedding) in enumerate(zip(data, embeddings)):
            # Create a unique ID for each item
            item_id = item.get('id', str(i))
            
            # Create point with valid ID (ensure it's an integer)
            try:
                point_id = int(item_id)
            except (ValueError, TypeError):
                point_id = i
            
            # Create payload based on collection type
            if collection_name == RESTAURANT_COLLECTION:
                # Extract menu items for payload
                menu_items = []
                items = item.get('items', [])
                if items is not None:
                    for menu_item in items:
                        if menu_item is not None:
                            menu_items.append({
                                'name': menu_item.get('name', ''),
                                'price': menu_item.get('price', 0)
                            })
                
                payload = {
                    'id': item_id,
                    'name': item.get('name', ''),
                    'address': item.get('address', ''),
                    'items': menu_items
                }
            else:  # HOTEL_COLLECTION
                # Extract rooms for payload
                rooms = []
                for room in item.get('rooms', []):
                    if room is not None:
                        rooms.append({
                            'name': room.get('name', ''),
                            'price': room.get('price', 0),
                            'description': room.get('description', '')
                        })
                
                # Extract amenities for payload
                amenities = []
                for amenity in item.get('amenities', []):
                    if amenity is not None:
                        amenities.append({
                            'name': amenity.get('name', ''),
                            'group': amenity.get('group_name', '')
                        })
                
                payload = {
                    'id': item_id,
                    'name': item.get('name', ''),
                    'address': item.get('address', ''),
                    'latitude': item.get('latitude'),
                    'longitude': item.get('longitude'),
                    'rooms': rooms,
                    'amenities': amenities
                }
            
            # Create point structure
            point = models.PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )
            points.append(point)
            
            # Upload in batches of 100 to avoid memory issues
            if len(points) >= 100 or i == len(data) - 1:
                client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                logging.info(f"Uploaded batch of {len(points)} items to '{collection_name}'")
                points = []
        
        logging.info(f"Data ingestion completed successfully for '{collection_name}'")
        return True
    except Exception as e:
        logging.error(f"Error ingesting data into '{collection_name}': {e}")
        return False

def refresh_restaurant_collection():
    """
    Refresh the restaurant collection in Qdrant
    """
    logging.info("Starting restaurant collection refresh...")
    
    # Initialize Qdrant client
    client = get_qdrant_client()
    
    # Delete existing collection
    delete_collection(client, RESTAURANT_COLLECTION)
    
    # Create new collection
    create_collection(client, RESTAURANT_COLLECTION)
    
    # Fetch restaurant data
    restaurants = fetch_restaurant_data()
    if not restaurants:
        logging.error("No restaurant data fetched, aborting refresh")
        return False
    
    # Create text representations
    restaurant_texts = create_restaurant_text_representations(restaurants)
    
    # Initialize embeddings manager
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    embeddings_manager = EmbeddingsManager(openai_api_key)
    
    # Generate embeddings
    logging.info("Generating embeddings for restaurants...")
    restaurant_embeddings = embeddings_manager.create_embeddings(restaurant_texts)
    logging.info(f"Generated {len(restaurant_embeddings)} restaurant embeddings")
    
    # Ingest data into Qdrant
    success = ingest_data_to_qdrant(client, RESTAURANT_COLLECTION, restaurants, restaurant_embeddings)
    
    return success

def refresh_hotel_collection():
    """
    Refresh the hotel collection in Qdrant
    """
    logging.info("Starting hotel collection refresh...")
    
    # Initialize Qdrant client
    client = get_qdrant_client()
    
    # Delete existing collection
    delete_collection(client, HOTEL_COLLECTION)
    
    # Create new collection
    create_collection(client, HOTEL_COLLECTION)
    
    # Fetch hotel data
    hotels = fetch_hotel_data()
    if not hotels:
        logging.error("No hotel data fetched, aborting refresh")
        return False
    
    # Create text representations
    hotel_texts = create_hotel_text_representations(hotels)
    
    # Initialize embeddings manager
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    embeddings_manager = EmbeddingsManager(openai_api_key)
    
    # Generate embeddings
    logging.info("Generating embeddings for hotels...")
    hotel_embeddings = embeddings_manager.create_embeddings(hotel_texts)
    logging.info(f"Generated {len(hotel_embeddings)} hotel embeddings")
    
    # Ingest data into Qdrant
    success = ingest_data_to_qdrant(client, HOTEL_COLLECTION, hotels, hotel_embeddings)
    
    return success

def main():
    """
    Main function to refresh all Qdrant collections
    """
    start_time = time.time()
    logging.info(f"Starting Qdrant collections refresh at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Refresh restaurant collection
    restaurant_success = refresh_restaurant_collection()
    if restaurant_success:
        logging.info("Restaurant collection refresh completed successfully")
    else:
        logging.error("Restaurant collection refresh failed")
    
    # Refresh hotel collection
    hotel_success = refresh_hotel_collection()
    if hotel_success:
        logging.info("Hotel collection refresh completed successfully")
    else:
        logging.error("Hotel collection refresh failed")
    
    # Log overall status
    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Qdrant collections refresh completed in {duration:.2f} seconds")
    
    if restaurant_success and hotel_success:
        logging.info("All collections refreshed successfully")
        return 0
    else:
        logging.error("Some collection refreshes failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
