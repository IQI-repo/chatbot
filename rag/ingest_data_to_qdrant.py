import os
import logging
import json
from dotenv import load_dotenv
from src.document_loader import DocumentLoader
from src.embeddings_manager import EmbeddingsManager
from src.qdrant_manager import QdrantManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def ingest_data():
    """
    Ingest restaurant data from JSON file into Qdrant vector database.
    """
    load_dotenv()
    
    # Check for required API keys
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
        document_loader = DocumentLoader('data/documents')
        embeddings_manager = EmbeddingsManager(openai_api_key)
        qdrant_manager = QdrantManager()
        
        # Load restaurant data
        logging.info("Loading restaurant data from JSON file...")
        restaurants_data = document_loader.load_json_data('data_fixed_formatted.json', use_streaming=True)
        logging.info(f"Loaded {len(restaurants_data)} restaurants from data file")
        
        if not restaurants_data:
            logging.error("No restaurant data loaded! Check file path and content.")
            return False
        
        # Create text representations for restaurants
        logging.info("Creating text representations...")
        restaurant_texts = []
        for restaurant in restaurants_data:
            # Basic restaurant info
            restaurant_text = f"Restaurant ID: {restaurant.get('id')}\n"
            restaurant_text += f"Name: {restaurant.get('name')}\n"
            restaurant_text += f"Address: {restaurant.get('address')}\n"
            
            # Menu items
            restaurant_text += "Menu items:\n"
            items = restaurant.get('items', [])
            if items is not None:
                for item in items:
                    if item is not None:
                        restaurant_text += f"- {item.get('name', 'Unknown')} - Price: {item.get('price', 0)} VND\n"
            
            restaurant_texts.append(restaurant_text)
        
        # Generate embeddings
        logging.info("Generating embeddings...")
        restaurant_embeddings = embeddings_manager.create_embeddings(restaurant_texts)
        logging.info(f"Generated {len(restaurant_embeddings)} embeddings")
        
        # Ingest data into Qdrant
        logging.info("Ingesting data into Qdrant...")
        success = qdrant_manager.ingest_data(restaurants_data, restaurant_embeddings)
        
        if success:
            logging.info("Data ingestion completed successfully!")
            return True
        else:
            logging.error("Data ingestion failed!")
            return False
            
    except Exception as e:
        logging.error(f"Error during data ingestion: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    ingest_data()
