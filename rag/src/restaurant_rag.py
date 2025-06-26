import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import openai
import json
import logging

from .document_loader import DocumentLoader
from .text_processor import TextProcessor
from .embeddings_manager import EmbeddingsManager
from .qdrant_manager import QdrantManager

class RestaurantRAG:
    """
    Specialized RAG system for restaurant and food data queries.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        logging.debug(f"OpenAI API key loaded: {'Present' if self.api_key else 'Missing'}")
        
        self.loader = DocumentLoader('data/documents')
        self.processor = TextProcessor()
        self.embeddings_manager = EmbeddingsManager(self.api_key)
        self.qdrant_manager = QdrantManager()
        self.restaurants_data = []
        
        # Initialize system
        logging.info("Initializing RestaurantRAG system")
        self.initialize_system()

    def initialize_system(self):
        """Load restaurant data and prepare for queries"""
        # Check if data has been loaded into Qdrant
        # For this implementation, we assume data has been loaded using the ingest_data_to_qdrant.py script
        # If you want to load data here, you would need to implement similar logic to the ingest script
        
        logging.info("RestaurantRAG system initialized with Qdrant vector database")
        logging.info("If you haven't ingested data yet, please run the ingest_data_to_qdrant.py script")
        
    def _create_text_representations(self, restaurants: List[Dict]) -> List[str]:
        """Create searchable text representations for restaurants.
        
        Args:
            restaurants: List of restaurant dictionaries
            
        Returns:
            List of text representations
        """
        texts = []
        for i, restaurant in enumerate(restaurants):
            try:
                # Basic restaurant info
                logging.debug(f"Processing restaurant {i}: {restaurant.get('name', 'Unknown')}")
                restaurant_text = f"Restaurant ID: {restaurant.get('id')}\n"
                restaurant_text += f"Name: {restaurant.get('name')}\n"
                restaurant_text += f"Address: {restaurant.get('address')}\n"
                
                # Menu items
                restaurant_text += "Menu items:\n"
                items = restaurant.get('items', [])
                logging.debug(f"Restaurant has {len(items)} menu items")
                for item in items:
                    restaurant_text += f"- {item.get('name')} - Price: {item.get('price')} VND\n"
                
                texts.append(restaurant_text)
            except Exception as e:
                logging.error(f"Error processing restaurant {i}: {e}")
                logging.error(f"Restaurant data: {restaurant}")
        
        logging.info(f"Created {len(texts)} restaurant text representations")
        return texts

    def search_restaurants(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for restaurants based on a query
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching restaurants with their details
        """
        # Get query embedding
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar restaurants
        results = self.qdrant_manager.search_restaurants(query_embedding.tolist(), top_k)
        
        return results
    
    def search_menu_items(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for specific menu items across all restaurants
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching menu items with restaurant info
        """
        logging.info(f"Searching menu items for query: {query}")
        
        # Get query embedding
        logging.debug("Creating embedding for query")
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar menu items
        results = self.qdrant_manager.search_menu_items(query_embedding.tolist(), top_k)
        
        logging.info(f"Returning {len(results)} menu item results")
        return results
    
    # Similarity calculation is now handled by Qdrant
    
    def answer_restaurant_query(self, query: str) -> str:
        """
        Answer a query about restaurants or food items using Qdrant vector database
        
        Args:
            query: The user's question about restaurants or food
            
        Returns:
            A natural language response to the query
        """
        # Search for relevant restaurants and menu items from Qdrant
        relevant_restaurants = self.search_restaurants(query, top_k=3)
        relevant_menu_items = self.search_menu_items(query, top_k=5)
        
        # Prepare context
        context = "Restaurant information:\n"
        
        # Add restaurant info from Qdrant results
        for restaurant in relevant_restaurants:
            context += f"Restaurant: {restaurant.get('name', 'Unknown')}\n"
            context += f"Address: {restaurant.get('address', 'No address')}\n"
            
            # Add some sample menu items
            context += "Sample menu items:\n"
            for item in restaurant.get('items', [])[:5]:  # Limit to 5 items per restaurant
                if item is not None:
                    context += f"- {item.get('name', 'Unknown')} - Price: {item.get('price', 0)} VND\n"
            
            context += "\n"
        
        # Add specific menu items that matched the query
        context += "Specific menu items that match your query:\n"
        for item_info in relevant_menu_items:
            item = item_info.get('item', {})
            restaurant_name = item_info.get('restaurant_name', 'Unknown restaurant')
            context += f"- {item.get('name', 'Unknown')} - Price: {item.get('price', 0)} VND at {restaurant_name}\n"
        
        # Create prompt
        prompt = f"""Context: {context}\n\nQuestion: {query}\n\nAnswer:"""
        
        # Get response from OpenAI (using v0.28.1 format)
        try:
            logging.debug("Sending request to OpenAI for restaurant query")
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specializing in Vietnamese restaurants and food. Use the provided context to answer the question in Vietnamese. If the information is not in the context, say you don't have that information."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract content from response (different format in v0.28.1)
            answer = response['choices'][0]['message']['content']
            logging.debug(f"Received answer from OpenAI: {answer[:50]}...")
            return answer
        except Exception as e:
            logging.error(f"Error getting response from OpenAI: {e}")
            return "Xin lỗi, tôi không thể trả lời câu hỏi của bạn lúc này."
