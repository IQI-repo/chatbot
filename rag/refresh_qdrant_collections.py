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
ORDERS_COLLECTION = "orders_collection"

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

def get_qdrant_client(max_retries=3, timeout=30.0):
    """
    Initialize and return a Qdrant client with retry logic
    
    Args:
        max_retries: Maximum number of connection attempts
        timeout: Connection timeout in seconds
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            if QDRANT_API_KEY:
                client = QdrantClient(
                    api_key=QDRANT_API_KEY,
                    url=QDRANT_URL,
                    port=QDRANT_PORT,
                    timeout=timeout
                )
                logging.info("Connected to Qdrant cloud service")
            else:
                client = QdrantClient(":memory:", timeout=timeout)  # In-memory storage for testing
                logging.info("Using in-memory Qdrant instance (no API key provided)")
            
            # Test connection by getting collections list
            try:
                client.get_collections()
                return client
            except Exception as e:
                logging.warning(f"Connection test failed: {e}")
                raise e
                
        except Exception as e:
            retry_count += 1
            last_exception = e
            wait_time = 2 ** retry_count  # Exponential backoff
            logging.warning(f"Qdrant connection attempt {retry_count}/{max_retries} failed: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # If we get here, all retries failed
    logging.error(f"Failed to connect to Qdrant after {max_retries} attempts: {last_exception}")
    
    # Fall back to in-memory client if cloud connection fails
    logging.warning("Falling back to in-memory Qdrant client")
    return QdrantClient(":memory:", timeout=timeout)

def create_collection(client, collection_name, max_retries=3):
    """
    Create a new collection in Qdrant with retry logic
    
    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to create
        max_retries: Maximum number of creation attempts
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            logging.info(f"Creating collection '{collection_name}' (attempt {retry_count + 1}/{max_retries})")
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
            return True
        except Exception as e:
            retry_count += 1
            last_exception = e
            wait_time = 2 ** retry_count  # Exponential backoff
            logging.warning(f"Collection creation attempt {retry_count}/{max_retries} failed: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # If we get here, all retries failed
    logging.error(f"Failed to create collection '{collection_name}' after {max_retries} attempts: {last_exception}")
    return False

def delete_collection(client, collection_name, max_retries=3):
    """
    Delete a collection from Qdrant if it exists with retry logic
    
    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to delete
        max_retries: Maximum number of deletion attempts
    """
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Check if collection exists
            try:
                collections = client.get_collections().collections
                collection_names = [collection.name for collection in collections]
                
                if collection_name not in collection_names:
                    logging.info(f"Collection '{collection_name}' does not exist, nothing to delete")
                    return True
            except Exception as e:
                logging.warning(f"Error checking if collection exists: {e}")
                # Continue with deletion attempt anyway
            
            logging.info(f"Deleting collection '{collection_name}' (attempt {retry_count + 1}/{max_retries})")
            client.delete_collection(collection_name=collection_name)
            logging.info(f"Collection '{collection_name}' deleted successfully")
            return True
            
        except Exception as e:
            retry_count += 1
            last_exception = e
            wait_time = 2 ** retry_count  # Exponential backoff
            logging.warning(f"Collection deletion attempt {retry_count}/{max_retries} failed: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    # If we get here, all retries failed
    logging.error(f"Failed to delete collection '{collection_name}' after {max_retries} attempts: {last_exception}")
    return False

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

def fetch_orders_data():
    """
    Fetch orders data from MySQL database
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch orders
        logging.info("Fetching orders from database...")
        cursor.execute("""
            SELECT o.*, u.name as user_name, u.phone as user_phone, u.email as user_email
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 1000
        """)
        orders = cursor.fetchall()
        logging.info(f"Fetched {len(orders)} orders")
        
        # Process each order to get order details
        for order in orders:
            order_id = order['id']
            
            # Fetch order details for this order
            cursor.execute("""
                SELECT od.*, 
                       COALESCE(i.name, hr.name, NULL) as item_name,
                       COALESCE(r.name, h.name, NULL) as service_name
                FROM orders od
                LEFT JOIN items i ON od.item_id = i.id
                LEFT JOIN restaurants r ON i.restaurant_id = r.id
                LEFT JOIN hotel_rooms hr ON od.room_id = hr.id
                LEFT JOIN hotels h ON hr.hotel_id = h.id
                WHERE od.order_id = %s
            """, (order_id,))
            order['details'] = cursor.fetchall()
            
        return orders
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching orders data: {err}")
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

def create_orders_text_representations(orders):
    """
    Create text representations for orders to generate embeddings
    """
    order_texts = []
    
    for order in orders:
        # Basic order info
        order_text = f"Order ID: {order.get('id')}\n"
        order_text += f"User ID: {order.get('user_id', 'Unknown')}\n"
        if order.get('user_name'):
            order_text += f"User Name: {order.get('user_name')}\n"
        if order.get('user_phone'):
            order_text += f"User Phone: {order.get('user_phone')}\n"
        if order.get('user_email'):
            order_text += f"User Email: {order.get('user_email')}\n"
            
        order_text += f"Service Type: {order.get('service_type', 'Unknown')}\n"
        order_text += f"Status: {order.get('status', 'Unknown')}\n"
        order_text += f"Total Amount: {order.get('total_amount', 0)} VND\n"
        order_text += f"Payment Method: {order.get('payment_method', 'Unknown')}\n"
        
        if order.get('created_at'):
            order_text += f"Created At: {order.get('created_at')}\n"
        
        if order.get('address'):
            order_text += f"Address: {order.get('address')}\n"
        
        if order.get('note'):
            order_text += f"Note: {order.get('note')}\n"
        
        # Order details
        if order.get('details'):
            order_text += "Order Details:\n"
            for detail in order.get('details', []):
                if detail.get('item_name'):
                    order_text += f"- {detail.get('item_name')}\n"
                    order_text += f"  Quantity: {detail.get('quantity', 1)}\n"
                    order_text += f"  Price: {detail.get('price', 0)} VND\n"
                    
                if detail.get('service_name'):
                    order_text += f"  Service: {detail.get('service_name')}\n"
                
                if detail.get('note'):
                    order_text += f"  Note: {detail.get('note')}\n"
        
        order_texts.append(order_text)
    
    return order_texts

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
            elif collection_name == HOTEL_COLLECTION:
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
            else:  # ORDERS_COLLECTION
                # Extract order details for payload
                details = []
                for detail in item.get('details', []):
                    if detail is not None:
                        details.append({
                            'item_name': detail.get('item_name', ''),
                            'service_name': detail.get('service_name', ''),
                            'quantity': detail.get('quantity', 1),
                            'price': detail.get('price', 0)
                        })
                
                payload = {
                    'id': item_id,
                    'user_id': item.get('user_id', ''),
                    'user_name': item.get('user_name', ''),
                    'service_type': item.get('service_type', ''),
                    'status': item.get('status', ''),
                    'total_amount': item.get('total_amount', 0),
                    'payment_method': item.get('payment_method', ''),
                    'created_at': str(item.get('created_at', '')),
                    'details': details
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
    
    try:
        # Initialize Qdrant client
        client = get_qdrant_client()
        
        # Delete existing collection
        if not delete_collection(client, RESTAURANT_COLLECTION):
            logging.warning("Failed to delete restaurant collection, but will try to continue")
        
        # Create new collection
        if not create_collection(client, RESTAURANT_COLLECTION):
            logging.error("Failed to create restaurant collection, aborting refresh")
            return False
        
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
    except Exception as e:
        logging.error(f"Unexpected error in restaurant collection refresh: {e}")
        return False

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

def refresh_orders_collection():
    """
    Refresh the orders collection in Qdrant
    """
    logging.info("Starting orders collection refresh...")
    
    # Initialize Qdrant client
    client = get_qdrant_client()
    
    # Delete existing collection
    delete_collection(client, ORDERS_COLLECTION)
    
    # Create new collection
    create_collection(client, ORDERS_COLLECTION)
    
    # Fetch orders data
    orders = fetch_orders_data()
    if not orders:
        logging.error("No orders data fetched, aborting refresh")
        return False
    
    # Create text representations
    order_texts = create_orders_text_representations(orders)
    
    # Initialize embeddings manager
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        logging.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    embeddings_manager = EmbeddingsManager(openai_api_key)
    
    # Generate embeddings
    logging.info("Generating embeddings for orders...")
    embeddings = []
    batch_size = 10  # Process in smaller batches to avoid timeouts
    
    for i in range(0, len(order_texts), batch_size):
        batch_texts = order_texts[i:i+batch_size]
        batch_embeddings = embeddings_manager.create_embeddings(batch_texts)
        embeddings.extend(batch_embeddings)
        logging.info(f"Generated embeddings for batch {i//batch_size + 1}/{(len(order_texts) + batch_size - 1)//batch_size}")
    
    # Ingest data to Qdrant
    success = ingest_data_to_qdrant(client, ORDERS_COLLECTION, orders, embeddings)
    
    if success:
        logging.info("Orders collection refreshed successfully")
    else:
        logging.error("Failed to refresh orders collection")
    
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
    
    # Refresh orders collection
    orders_success = refresh_orders_collection()
    if orders_success:
        logging.info("Orders collection refresh completed successfully")
    else:
        logging.error("Orders collection refresh failed")
    
    # Log overall status
    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Qdrant collections refresh completed in {duration:.2f} seconds")
    
    if restaurant_success and hotel_success and orders_success:
        logging.info("All collections refreshed successfully")
        return 0
    else:
        logging.warning("Some collections failed to refresh")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
