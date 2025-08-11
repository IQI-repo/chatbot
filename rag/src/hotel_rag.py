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

class HotelQdrantManager(QdrantManager):
    """
    Specialized QdrantManager for hotel data that uses a different collection name.
    """
    def __init__(self):
        super().__init__()
        self.collection_name = "hotel_collection"
        # Ensure collection exists with the new name
        self._create_collection_if_not_exists()
        
    def search_hotels(self, query_embedding: List[float], top_k: int = 3) -> List[Dict]:
        """
        Search for hotels based on a query embedding.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching hotels with their details
        """
        try:
            logging.info(f"Searching for top {top_k} hotels")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract hotel data from search results
            hotels = []
            for result in search_result:
                hotel_data = result.payload
                hotel_data['score'] = result.score
                hotels.append(hotel_data)
                
            logging.info(f"Found {len(hotels)} matching hotels")
            return hotels
        except Exception as e:
            logging.error(f"Error searching for hotels: {e}")
            return []
    
    def search_hotel_rooms(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """
        Search for specific hotel rooms across all hotels.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching hotel rooms with hotel info
        """
        try:
            # First get matching hotels
            hotels = self.search_hotels(query_embedding, top_k)
            
            # Extract room information
            rooms_results = []
            for hotel in hotels:
                hotel_name = hotel.get('name', 'Unknown')
                hotel_id = hotel.get('id')
                
                for room in hotel.get('rooms', []):
                    if room is not None:
                        rooms_results.append({
                            'room': room,
                            'hotel_name': hotel_name,
                            'hotel_id': hotel_id
                        })
            
            logging.info(f"Found {len(rooms_results)} matching rooms")
            return rooms_results[:top_k]  # Limit to top_k results
        except Exception as e:
            logging.error(f"Error searching for hotel rooms: {e}")
            return []

class HotelRAG:
    """
    Specialized RAG system for hotel data queries.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        logging.debug(f"OpenAI API key loaded: {'Present' if self.api_key else 'Missing'}")
        
        self.processor = TextProcessor()
        self.embeddings_manager = EmbeddingsManager(self.api_key)
        self.qdrant_manager = HotelQdrantManager()
        
        # Initialize system
        logging.info("Initializing HotelRAG system")
        self.initialize_system()

    def initialize_system(self):
        """Load hotel data and prepare for queries"""
        # Check if data has been loaded into Qdrant
        # For this implementation, we assume data has been loaded using the ingest_hotel_data_to_qdrant.py script
        
        logging.info("HotelRAG system initialized with Qdrant vector database")
        logging.info("If you haven't ingested data yet, please run the ingest_hotel_data_to_qdrant.py script")
    
    def search_hotels(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for hotels based on a query
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching hotels with their details
        """
        # Get query embedding
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar hotels
        results = self.qdrant_manager.search_hotels(query_embedding.tolist(), top_k)
        
        return results
    
    def search_hotel_rooms(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for specific hotel rooms across all hotels
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching hotel rooms with hotel info
        """
        logging.info(f"Searching hotel rooms for query: {query}")
        
        # Get query embedding
        logging.debug("Creating embedding for query")
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar hotel rooms
        rooms_results = self.qdrant_manager.search_hotel_rooms(query_embedding.tolist(), top_k)
        
        logging.info(f"Returning {len(rooms_results)} hotel room results")
        return rooms_results
    
    def extract_location_info(self, query: str) -> Dict:
        """
        Extract location information from a query using OpenAI
        
        Args:
            query: The user's question about hotels
            
        Returns:
            Dictionary with location information if found
        """
        try:
            logging.debug("Extracting location information from query")
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a location extraction assistant. Extract any location or place names mentioned in the query. If no location is mentioned, return 'None'. Only return the location name, nothing else."},
                    {"role": "user", "content": query}
                ]
            )
            
            location = response['choices'][0]['message']['content'].strip()
            if location.lower() == 'none':
                return None
                
            logging.debug(f"Extracted location: {location}")
            return location
        except Exception as e:
            logging.error(f"Error extracting location: {e}")
            return None
    
    def answer_hotel_query(self, query: str) -> Dict:
        """
        Answer a query about hotels using Qdrant vector database
        
        Args:
            query: The user's question about hotels
            
        Returns:
            A dictionary containing the answer and relevant hotels/rooms
        """
        # Extract location information if present in the query
        location = self.extract_location_info(query)
        
        # Search for relevant hotels and rooms from Qdrant
        relevant_hotels = self.search_hotels(query, top_k=3)
        relevant_rooms = self.search_hotel_rooms(query, top_k=5)
        
        # Prepare context
        context = "Hotel information:\n"
        
        # Add hotel info from Qdrant results
        for hotel in relevant_hotels:
            context += f"Hotel: {hotel.get('name', 'Unknown')}\n"
            context += f"Address: {hotel.get('address', 'No address')}\n"
            
            # Add coordinates if available
            if hotel.get('latitude') and hotel.get('longitude'):
                context += f"Coordinates: {hotel.get('latitude')}, {hotel.get('longitude')}\n"
            
            # Add amenities if available
            if hotel.get('amenities'):
                context += "Amenities:\n"
                amenities_seen = set()
                for amenity in hotel.get('amenities', []):
                    amenity_name = amenity.get('name', '')
                    if amenity_name and amenity_name not in amenities_seen:
                        amenities_seen.add(amenity_name)
                        context += f"- {amenity_name}\n"
            
            # Add some sample rooms
            context += "Sample rooms:\n"
            for room in hotel.get('rooms', [])[:3]:  # Limit to 3 rooms per hotel
                if room is not None:
                    context += f"- {room.get('name', 'Unknown')} - Price: {room.get('price', 0)} VND\n"
            
            context += "\n"
        
        # Add specific rooms that matched the query
        context += "Specific rooms that match your query:\n"
        for room_info in relevant_rooms:
            room = room_info.get('room', {})
            hotel_name = room_info.get('hotel_name', 'Unknown hotel')
            context += f"- {room.get('name', 'Unknown')} - Price: {room.get('price', 0)} VND at {hotel_name}\n"
        
        # Get the system prompt for hotel context
        from src.system_prompt import get_system_prompt_by_context
        system_prompt = get_system_prompt_by_context("hotel")
        
        # Add location awareness to the system prompt if location is detected
        if location:
            location_info = f"\n\nNgười dùng đang hỏi về khách sạn gần '{location}'. "
            location_info += "Hãy chú ý đặc biệt đến vị trí khách sạn và khoảng cách đến địa điểm này. "
            location_info += "Nếu có tọa độ, hãy sử dụng chúng để xác định khách sạn nào gần địa điểm được đề cập nhất."
            system_prompt += location_info
        
        # Create prompt
        prompt = f"""Context: {context}\n\nQuestion: {query}\n\nAnswer:"""
        
        # Get response from OpenAI (using v0.28.1 format)
        try:
            logging.debug("Sending request to OpenAI for hotel query")
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract content from response (different format in v0.28.1)
            answer = response['choices'][0]['message']['content']
            logging.debug(f"Received answer from OpenAI: {answer[:50]}...")
            
            return {
                "answer": answer,
                "top_hotels": relevant_hotels,
                "top_rooms": relevant_rooms
            }
        except Exception as e:
            logging.error(f"Error getting response from OpenAI: {e}")
            return {
                "answer": "Xin lỗi, tôi không thể trả lời câu hỏi của bạn lúc này.",
                "top_hotels": [],
                "top_rooms": []
            }
