#!/usr/bin/env python3
"""
Script to ingest delivery data from MySQL database into Qdrant vector database.
This creates embeddings for delivery-related data and stores them in Qdrant for semantic search.
"""

import os
import logging
import json
import mysql.connector
import numpy as np
from dotenv import load_dotenv
from src.embeddings_manager import EmbeddingsManager
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

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
DELIVERY_COLLECTION = "delivery_collection"

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

def fetch_delivery_data(cursor):
    """
    Fetch delivery data from MySQL database
    """
    try:
        # Fetch delivery records
        logging.info("Fetching delivery data from database...")
        cursor.execute("""
            SELECT * 
            FROM delivery
        """)
        deliveries = cursor.fetchall()
        logging.info(f"Fetched {len(deliveries)} delivery records")
        
        if not deliveries:
            logging.error("No delivery records found")
            return []
        
        # Print the first delivery record to see its structure
        if deliveries:
            logging.info(f"Sample delivery record keys: {list(deliveries[0].keys())}")
        
        # For each delivery, fetch related data
        for delivery in deliveries:
            # Use the primary key field from the actual schema
            # Based on the error, it seems 'id' might not be the primary key field
            # Let's try to find the actual primary key or use a fallback
            if 'id' in delivery:
                delivery_id = delivery['id']
            elif 'delivery_id' in delivery:
                delivery_id = delivery['delivery_id']
            else:
                # If we can't find a proper ID, skip this record
                logging.warning(f"Could not find ID field in delivery record: {list(delivery.keys())}")
                continue
            
            # Fetch service_taxi_model for this delivery
            if delivery.get('taxi_model_id'):
                cursor.execute("""
                    SELECT * FROM service_taxi_model
                    WHERE id = %s
                """, (delivery.get('taxi_model_id'),))
                delivery['service_model'] = cursor.fetchone() or {}
            else:
                delivery['service_model'] = {}
            
            # Fetch delivery_running for this delivery
            cursor.execute("""
                SELECT * FROM delivery_running
                WHERE delivery_id = %s
            """, (delivery_id,))
            delivery['running_status'] = cursor.fetchall()
            
            # Fetch order_point_delivery for this delivery
            cursor.execute("""
                SELECT * FROM order_point_delivery
                WHERE delivery_id = %s
            """, (delivery_id,))
            delivery['order_points'] = cursor.fetchall()
            
            # Fetch delivery_setting for this delivery
            cursor.execute("""
                SELECT * FROM delivery_setting
                WHERE delivery_id = %s
            """, (delivery_id,))
            delivery['settings'] = cursor.fetchall()
            
            # Fetch paybook_history_delivery for this delivery
            cursor.execute("""
                SELECT * FROM paybook_history_delivery
                WHERE delivery_id = %s
            """, (delivery_id,))
            delivery['payment_history'] = cursor.fetchall()
        
        return deliveries
        
    except mysql.connector.Error as err:
        logging.error(f"Error fetching delivery data: {err}")
        return []
    finally:
        # Don't close the cursor here, it will be closed in the main function
        pass

def prepare_delivery_data_for_embedding(deliveries):
    """
    Prepare delivery data for embedding by creating text representations
    
    Args:
        deliveries: List of delivery records with related data
        
    Returns:
        List of text representations and original delivery data
    """
    texts = []
    processed_deliveries = []
    
    def prepare_delivery_text(delivery):
        """
        Prepare a textual representation of a delivery record for embedding
        """
        # Basic delivery info
        delivery_id = delivery.get('id', 'Unknown')
        
        # Construct text representation
        text = f"Delivery ID: {delivery_id}\n"
        
        # Add other relevant fields if available
        if 'type_id' in delivery:
            text += f"Type ID: {delivery.get('type_id', 'Not specified')}\n"
        
        if 'user_id' in delivery:
            text += f"User ID: {delivery.get('user_id', 'Not specified')}\n"
        
        if 'order' in delivery:
            text += f"Order: {delivery.get('order', 'Not specified')}\n"
        
        if 'vehicle_description' in delivery:
            text += f"Vehicle: {delivery.get('vehicle_description', 'Not specified')}\n"
        
        # Add running status if available
        if 'running_status' in delivery and delivery['running_status']:
            status = delivery['running_status'][0]  # Take the first status record
            text += f"Status: {status.get('status', 'Unknown')}\n"
            if 'date_in' in status and status['date_in']:
                text += f"Date In: {status['date_in']}\n"
            if 'date_out' in status and status['date_out']:
                text += f"Date Out: {status['date_out']}\n"
        
        # Add service model info if available
        if 'service_model' in delivery and delivery['service_model']:
            model = delivery['service_model']
            text += f"Service Model: {model.get('name', 'Unknown')}\n"
            if 'image' in model and model['image']:
                text += f"Model Image: {model['image']}\n"
        
        # Add order points if available
        if 'order_points' in delivery and delivery['order_points']:
            text += "Order Points:\n"
            for idx, point in enumerate(delivery['order_points'], 1):
                text += f"  Point {idx}: {point.get('location_name', 'Unknown location')}\n"
        
        # Add settings if available
        if 'settings' in delivery and delivery['settings']:
            text += "Delivery Settings:\n"
            for setting in delivery['settings']:
                text += f"  {setting.get('setting_key', 'Unknown setting')}: {setting.get('setting_value', 'Not specified')}\n"
        
        return text
    
    for delivery in deliveries:
        text = prepare_delivery_text(delivery)
        texts.append(text)
        
        # Create a clean copy of delivery data for storage
        clean_delivery = {
            'id': delivery.get('id'),
            'name': delivery.get('name'),
            'delivery_type': delivery.get('delivery_type_name'),
            'price': delivery.get('price'),
            'description': delivery.get('description'),
            'service_area': delivery.get('service_area'),
            'created_at': str(delivery.get('created_at')) if delivery.get('created_at') else None,
            'updated_at': str(delivery.get('updated_at')) if delivery.get('updated_at') else None
        }
        
        # Add service models
        service_models = []
        for model in delivery.get('service_models', []):
            service_models.append({
                'id': model.get('id'),
                'name': model.get('name'),
                'price': model.get('price'),
                'description': model.get('description')
            })
        clean_delivery['service_models'] = service_models
        
        # Add order points
        order_points = []
        for point in delivery.get('order_points', []):
            order_points.append({
                'id': point.get('id'),
                'name': point.get('name'),
                'address': point.get('address'),
                'latitude': point.get('latitude'),
                'longitude': point.get('longitude')
            })
        clean_delivery['order_points'] = order_points
        
        # Add settings
        settings = {}
        for setting in delivery.get('settings', []):
            key = setting.get('key')
            if key:
                settings[key] = setting.get('value')
        clean_delivery['settings'] = settings
        
        processed_deliveries.append(clean_delivery)
    
    return texts, processed_deliveries

def initialize_qdrant_client():
    """
    Initialize Qdrant client and create collection if it doesn't exist
    
    Returns:
        Qdrant client instance
    """
    try:
        if QDRANT_API_KEY:
            # Use cloud Qdrant with API key
            client = QdrantClient(
                api_key=QDRANT_API_KEY,
                url=QDRANT_URL,
                port=QDRANT_PORT
            )
            logging.info("Connected to Qdrant cloud service")
        else:
            # Use local Qdrant
            client = QdrantClient(":memory:")  # In-memory storage for testing
            logging.info("Using in-memory Qdrant instance")
        
        # Check if collection exists, if not create it
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if DELIVERY_COLLECTION not in collection_names:
            logging.info(f"Creating collection: {DELIVERY_COLLECTION}")
            client.create_collection(
                collection_name=DELIVERY_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE)
            )
        else:
            logging.info(f"Collection {DELIVERY_COLLECTION} already exists")
            
            # Recreate collection if requested
            recreate = os.getenv('RECREATE_COLLECTIONS', 'false').lower() == 'true'
            if recreate:
                logging.info(f"Recreating collection: {DELIVERY_COLLECTION}")
                client.delete_collection(collection_name=DELIVERY_COLLECTION)
                client.create_collection(
                    collection_name=DELIVERY_COLLECTION,
                    vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE)
                )
        
        return client
    except Exception as e:
        logging.error(f"Error initializing Qdrant client: {e}")
        raise

def ingest_delivery_data_to_qdrant():
    """
    Main function to ingest delivery data from MySQL to Qdrant
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
        embeddings_manager = EmbeddingsManager(openai_api_key)
        qdrant_client = initialize_qdrant_client()
        
        # Fetch delivery data from MySQL
        logging.info("Fetching delivery data from MySQL...")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        deliveries = fetch_delivery_data(cursor)
        
        if not deliveries:
            logging.error("No delivery data found or error fetching data")
            return False
        
        # Prepare data for embedding
        logging.info("Preparing delivery data for embedding...")
        texts, processed_deliveries = prepare_delivery_data_for_embedding(deliveries)
        
        # Create embeddings
        logging.info(f"Creating embeddings for {len(texts)} delivery records...")
        embeddings = embeddings_manager.create_embeddings(texts)
        
        # Ingest data into Qdrant
        logging.info("Ingesting delivery data into Qdrant...")
        
        # Prepare points for batch upload
        points = []
        for i, (embedding, delivery) in enumerate(zip(embeddings, processed_deliveries)):
            points.append(models.PointStruct(
                id=i,
                vector=embedding.tolist(),
                payload=delivery
            ))
        
        # Upload in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            qdrant_client.upsert(
                collection_name=DELIVERY_COLLECTION,
                points=batch
            )
            logging.info(f"Uploaded batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")
        
        logging.info("Delivery data ingestion completed successfully!")
        return True
            
    except Exception as e:
        logging.error(f"Error during delivery data ingestion: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = ingest_delivery_data_to_qdrant()
    if success:
        print("Delivery data ingestion completed successfully!")
    else:
        print("Delivery data ingestion failed!")
