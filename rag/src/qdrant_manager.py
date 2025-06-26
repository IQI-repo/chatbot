import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

class QdrantManager:
    """
    Manager for Qdrant vector database operations.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('QDRANT_API_KEY')
        self.collection_name = "restaurant_collection"
        self.embedding_size = 1536  # OpenAI Ada embedding size
        
        # Initialize Qdrant client
        logging.info("Initializing Qdrant client")
        try:
            if self.api_key:
                # Use cloud Qdrant with API key
                self.client = QdrantClient(
                    api_key=self.api_key,
                    url="https://16f1329c-7600-4be6-8dc1-376daff8d555.us-west-1-0.aws.cloud.qdrant.io",
                    port=6333
                )
                logging.info("Connected to Qdrant cloud service")
            else:
                # Use local Qdrant
                self.client = QdrantClient(":memory:")  # In-memory storage for testing
                logging.info("Using in-memory Qdrant instance")
                
            # Ensure collection exists
            self._create_collection_if_not_exists()
        except Exception as e:
            logging.error(f"Error initializing Qdrant client: {e}")
            raise
    
    def _create_collection_if_not_exists(self):
        """Create the vector collection if it doesn't exist or recreate it if requested."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            # Only create if it doesn't exist
            if self.collection_name not in collection_names:
                logging.info(f"Creating collection '{self.collection_name}'")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_size,
                        distance=Distance.COSINE
                    ),
                    # Create payload indexes for faster filtering
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=0  # Index all vectors
                    )
                )
                logging.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logging.info(f"Collection '{self.collection_name}' already exists, using existing collection")
        except Exception as e:
            logging.error(f"Error creating/recreating collection: {e}")
            raise
    
    def ingest_data(self, restaurants_data: List[Dict], embeddings: List[np.ndarray]) -> bool:
        """
        Ingest restaurant data and embeddings into Qdrant.
        
        Args:
            restaurants_data: List of restaurant dictionaries
            embeddings: List of embeddings corresponding to restaurants_data
            
        Returns:
            True if ingestion was successful, False otherwise
        """
        try:
            logging.info(f"Ingesting {len(restaurants_data)} restaurants into Qdrant")
            
            # Prepare points for batch upload
            points = []
            for i, (restaurant, embedding) in enumerate(zip(restaurants_data, embeddings)):
                # Create a unique ID for each restaurant
                restaurant_id = restaurant.get('id', str(i))
                
                # Extract menu items for payload
                menu_items = []
                items = restaurant.get('items', [])
                if items is not None:
                    for item in items:
                        if item is not None:
                            menu_items.append({
                                'name': item.get('name', ''),
                                'price': item.get('price', 0)
                            })
                
                # Create point with valid ID (ensure it's an integer)
                # Try to convert restaurant_id to int if possible, otherwise use a counter
                try:
                    point_id = int(restaurant_id)
                except (ValueError, TypeError):
                    point_id = i
                    
                point = PointStruct(
                    id=point_id,  # Use integer ID
                    vector=embedding.tolist(),  # Convert numpy array to list
                    payload={
                        'id': restaurant_id,
                        'name': restaurant.get('name', ''),
                        'address': restaurant.get('address', ''),
                        'items': menu_items
                    }
                )
                points.append(point)
                
                # Upload in batches of 100 to avoid memory issues
                if len(points) >= 100 or i == len(restaurants_data) - 1:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    logging.info(f"Uploaded batch of {len(points)} restaurants")
                    points = []
            
            logging.info("Data ingestion completed successfully")
            return True
        except Exception as e:
            logging.error(f"Error ingesting data into Qdrant: {e}")
            return False
    
    def search_restaurants(self, query_embedding: List[float], top_k: int = 3) -> List[Dict]:
        """
        Search for restaurants based on a query embedding.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching restaurants with their details
        """
        try:
            logging.info(f"Searching for top {top_k} restaurants")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract restaurant data from search results
            restaurants = []
            for scored_point in search_result:
                restaurant = scored_point.payload
                restaurant['score'] = scored_point.score  # Add similarity score
                restaurants.append(restaurant)
            
            logging.info(f"Found {len(restaurants)} matching restaurants")
            return restaurants
        except Exception as e:
            logging.error(f"Error searching restaurants: {e}")
            return []
    
    def search_menu_items(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """
        Search for specific menu items across all restaurants.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching menu items with restaurant info
        """
        try:
            logging.info(f"Searching for top {top_k} menu items")
            
            # First, get a larger set of restaurants that might have matching items
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k * 3  # Get more restaurants to find the best menu items
            )
            
            # Extract and flatten menu items from search results
            menu_items_info = []
            for scored_point in search_result:
                restaurant = scored_point.payload
                restaurant_id = restaurant.get('id')
                restaurant_name = restaurant.get('name')
                
                for item in restaurant.get('items', []):
                    menu_items_info.append({
                        'restaurant_id': restaurant_id,
                        'restaurant_name': restaurant_name,
                        'item': item,
                        'score': scored_point.score  # Use restaurant score as initial ranking
                    })
            
            # Sort by score and take top_k
            menu_items_info.sort(key=lambda x: x['score'], reverse=True)
            top_items = menu_items_info[:top_k]
            
            logging.info(f"Found {len(top_items)} matching menu items")
            return top_items
        except Exception as e:
            logging.error(f"Error searching menu items: {e}")
            return []
