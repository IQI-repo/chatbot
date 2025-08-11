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
            SELECT h.*, ht.name as type_name 
            FROM hotel h
            LEFT JOIN hotel_type ht ON h.type_id = ht.id
            WHERE h.is_active = 1
        """)
        hotels = cursor.fetchall()
        logging.info(f"Fetched {len(hotels)} hotels")
        
        # Process each hotel to get rooms and amenities
        for hotel in hotels:
            hotel_id = hotel['id']
            
            # Fetch rooms for this hotel
            cursor.execute("""
                SELECT * FROM hotel_room 
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
                SELECT * FROM hotel_image
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

def create_text_representations(hotels):
    """
    Create text representations for hotels to generate embeddings
    """
    hotel_texts = []
    
    for hotel in hotels:
        # Basic hotel info
        hotel_text = f"Hotel ID: {hotel.get('id')}\n"
        hotel_text += f"Name: {hotel.get('name', 'Unknown')}\n"
        hotel_text += f"Type: {hotel.get('type_name', 'Unknown')}\n"
        hotel_text += f"Address: {hotel.get('address', 'Unknown')}\n"
        hotel_text += f"Location: Latitude {hotel.get('latitude', 'Unknown')}, Longitude {hotel.get('longitude', 'Unknown')}\n"
        hotel_text += f"Rating: {hotel.get('star', 0)} stars, {hotel.get('rating_point', 0)} points from {hotel.get('rating_count', 0)} reviews\n"
        
        if hotel.get('description'):
            hotel_text += f"Description: {hotel.get('description')}\n"
        
        if hotel.get('general_policy'):
            hotel_text += f"General Policy: {hotel.get('general_policy')}\n"
        
        # Amenities
        if hotel.get('amenities'):
            hotel_text += "Amenities:\n"
            for amenity in hotel.get('amenities', []):
                hotel_text += f"- {amenity.get('name', 'Unknown')}\n"
        
        # Rooms
        if hotel.get('rooms'):
            hotel_text += "Rooms:\n"
            for room in hotel.get('rooms', []):
                hotel_text += f"- {room.get('name', 'Unknown')} Room\n"
                hotel_text += f"  Capacity: {room.get('qty_people', 0)} people, Size: {room.get('acreage', 0)} sqm\n"
                hotel_text += f"  Price: {room.get('price', 0)} VND"
                if room.get('discount_price'):
                    hotel_text += f", Discounted: {room.get('discount_price')} VND ({room.get('discount_rate', 0)}% off)\n"
                else:
                    hotel_text += "\n"
                
                if room.get('view'):
                    hotel_text += f"  View: {room.get('view')}\n"
                if room.get('description'):
                    hotel_text += f"  Description: {room.get('description')}\n"
        
        hotel_texts.append(hotel_text)
    
    return hotel_texts

def ingest_hotel_data_to_qdrant():
    """
    Main function to ingest hotel data from MySQL to Qdrant
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
        
        # Create a custom QdrantManager for hotels
        class HotelQdrantManager(QdrantManager):
            def __init__(self):
                super().__init__()
                self.collection_name = "hotel_collection"  # Use a different collection for hotels
                self._create_collection_if_not_exists()
            
            def ingest_hotel_data(self, hotels_data, embeddings):
                """
                Ingest hotel data and embeddings into Qdrant.
                """
                try:
                    logging.info(f"Ingesting {len(hotels_data)} hotels into Qdrant")
                    
                    # Prepare points for batch upload
                    points = []
                    for i, (hotel, embedding) in enumerate(zip(hotels_data, embeddings)):
                        # Create a unique ID for each hotel
                        hotel_id = hotel.get('id', str(i))
                        
                        # Extract rooms for payload
                        rooms = []
                        for room in hotel.get('rooms', []):
                            rooms.append({
                                'id': room.get('id'),
                                'name': room.get('name', ''),
                                'price': room.get('price', 0),
                                'discount_price': room.get('discount_price', 0),
                                'capacity': room.get('qty_people', 0),
                                'size': room.get('acreage', 0),
                                'view': room.get('view', '')
                            })
                        
                        # Extract amenities for payload
                        amenities = []
                        for amenity in hotel.get('amenities', []):
                            amenities.append({
                                'id': amenity.get('id'),
                                'name': amenity.get('name', '')
                            })
                        
                        # Create point with valid ID (ensure it's an integer)
                        try:
                            point_id = int(hotel_id)
                        except (ValueError, TypeError):
                            point_id = i
                            
                        point = models.PointStruct(
                            id=point_id,
                            vector=embedding.tolist(),
                            payload={
                                'id': hotel_id,
                                'name': hotel.get('name', ''),
                                'type': hotel.get('type_name', ''),
                                'address': hotel.get('address', ''),
                                'star': hotel.get('star', 0),
                                'rating_point': hotel.get('rating_point', 0),
                                'rating_count': hotel.get('rating_count', 0),
                                'latitude': hotel.get('latitude'),
                                'longitude': hotel.get('longitude'),
                                'description': hotel.get('description', ''),
                                'rooms': rooms,
                                'amenities': amenities
                            }
                        )
                        points.append(point)
                        
                        # Upload in batches of 100 to avoid memory issues
                        if len(points) >= 100 or i == len(hotels_data) - 1:
                            self.client.upsert(
                                collection_name=self.collection_name,
                                points=points
                            )
                            logging.info(f"Uploaded batch of {len(points)} hotels")
                            points = []
                    
                    logging.info("Hotel data ingestion completed successfully")
                    return True
                except Exception as e:
                    logging.error(f"Error ingesting hotel data into Qdrant: {e}")
                    return False
        
        # Initialize the hotel Qdrant manager
        hotel_qdrant_manager = HotelQdrantManager()
        
        # Fetch hotel data from MySQL
        logging.info("Fetching hotel data from MySQL...")
        hotels_data = fetch_hotel_data()
        
        if not hotels_data:
            logging.error("No hotel data loaded! Check database connection and queries.")
            return False
        
        # Create text representations for hotels
        logging.info("Creating text representations...")
        hotel_texts = create_text_representations(hotels_data)
        
        # Generate embeddings
        logging.info("Generating embeddings...")
        hotel_embeddings = embeddings_manager.create_embeddings(hotel_texts)
        logging.info(f"Generated {len(hotel_embeddings)} embeddings")
        
        # Ingest data into Qdrant
        logging.info("Ingesting hotel data into Qdrant...")
        success = hotel_qdrant_manager.ingest_hotel_data(hotels_data, hotel_embeddings)
        
        if success:
            logging.info("Hotel data ingestion completed successfully!")
            return True
        else:
            logging.error("Hotel data ingestion failed!")
            return False
            
    except Exception as e:
        logging.error(f"Error during hotel data ingestion: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    ingest_hotel_data_to_qdrant()
