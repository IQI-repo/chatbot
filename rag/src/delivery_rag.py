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
from .system_prompt import get_system_prompt_by_context

class DeliveryQdrantManager(QdrantManager):
    """
    Specialized QdrantManager for delivery data that uses a different collection name.
    """
    def __init__(self):
        super().__init__()
        self.collection_name = "delivery_collection"
        # Ensure collection exists with the new name
        self._create_collection_if_not_exists()
        
    def search_delivery_data(self, query_embedding: List[float], top_k: int = 3) -> List[Dict]:
        """
        Search for delivery data based on a query embedding.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching delivery data with their details
        """
        try:
            logging.info(f"Searching for top {top_k} delivery records")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract delivery data from search results
            delivery_data = []
            for result in search_result:
                data = result.payload
                data['score'] = result.score
                delivery_data.append(data)
                
            logging.info(f"Found {len(delivery_data)} matching delivery records")
            return delivery_data
        except Exception as e:
            logging.error(f"Error searching for delivery data: {e}")
            return []
    
    def search_delivery_details(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """
        Search for specific delivery details like delivery types, pricing, etc.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching delivery details
        """
        try:
            # First get matching delivery records
            delivery_records = self.search_delivery_data(query_embedding, top_k)
            
            # Extract detailed information
            details_results = []
            for record in delivery_records:
                delivery_id = record.get('id')
                delivery_type = record.get('delivery_type', 'Unknown')
                
                # Add detailed information
                details_results.append({
                    'delivery_id': delivery_id,
                    'delivery_type': delivery_type,
                    'details': record
                })
            
            logging.info(f"Found {len(details_results)} matching delivery details")
            return details_results[:top_k]  # Limit to top_k results
        except Exception as e:
            logging.error(f"Error searching for delivery details: {e}")
            return []

class DeliveryRAG:
    """
    Specialized RAG system for delivery data queries.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        logging.debug(f"OpenAI API key loaded: {'Present' if self.api_key else 'Missing'}")
        
        self.processor = TextProcessor()
        self.embeddings_manager = EmbeddingsManager(self.api_key)
        self.qdrant_manager = DeliveryQdrantManager()
        
        # Initialize system
        logging.info("Initializing DeliveryRAG system")
        self.initialize_system()

    def initialize_system(self):
        """Load delivery data and prepare for queries"""
        # Check if data has been loaded into Qdrant
        # For this implementation, we assume data has been loaded using the ingest_delivery_data_to_qdrant.py script
        
        logging.info("DeliveryRAG system initialized with Qdrant vector database")
        logging.info("If you haven't ingested data yet, please run the ingest_delivery_data_to_qdrant.py script")
    
    def search_delivery_data(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for delivery data based on a query
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching delivery data with their details
        """
        # Get query embedding
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar delivery data
        results = self.qdrant_manager.search_delivery_data(query_embedding.tolist(), top_k)
        
        return results
    
    def search_delivery_details(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for specific delivery details
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching delivery details
        """
        logging.info(f"Searching delivery details for query: {query}")
        
        # Get query embedding
        logging.debug("Creating embedding for query")
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar delivery details
        results = self.qdrant_manager.search_delivery_details(query_embedding.tolist(), top_k)
        
        return results
    
    def extract_location_info(self, query: str) -> Optional[Dict[str, str]]:
        """
        Extract location information from the query if present
        
        Args:
            query: The user's query
            
        Returns:
            Dictionary with location information or None if not found
        """
        try:
            logging.info("Extracting location information from query")
            
            # Use OpenAI to extract location information
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là một trợ lý trích xuất thông tin. Hãy trích xuất thông tin về địa điểm từ câu hỏi của người dùng. Nếu không có thông tin về địa điểm, hãy trả về 'None'. Nếu có, hãy trả về dưới dạng JSON với các trường: city (thành phố), district (quận/huyện), và address (địa chỉ cụ thể nếu có). Chỉ trả về JSON, không có văn bản giải thích."},
                    {"role": "user", "content": query}
                ]
            )
            
            location_text = response['choices'][0]['message']['content']
            
            # If the response is 'None', return None
            if 'None' in location_text and len(location_text) < 10:
                return None
                
            # Try to parse JSON from the response
            try:
                # Extract JSON from the response if it's embedded in text
                if '{' in location_text and '}' in location_text:
                    json_start = location_text.find('{')
                    json_end = location_text.rfind('}') + 1
                    json_str = location_text[json_start:json_end]
                    location_data = json.loads(json_str)
                else:
                    location_data = json.loads(location_text)
                
                return location_data
            except json.JSONDecodeError:
                logging.error(f"Failed to parse location JSON: {location_text}")
                return None
                
        except Exception as e:
            logging.error(f"Error extracting location info: {e}")
            return None
    
    def answer_delivery_query(self, query: str) -> Dict:
        """
        Answer a query about delivery services
        
        Args:
            query: The user's question about delivery services
            
        Returns:
            A dictionary with the answer and relevant delivery data
        """
        # Extract location information if present in the query
        location = self.extract_location_info(query)
        
        # Search for relevant delivery data from Qdrant
        relevant_delivery_data = self.search_delivery_data(query, top_k=3)
        relevant_delivery_details = self.search_delivery_details(query, top_k=5)
        
        # Prepare context
        context = "Thông tin về dịch vụ giao hàng:\n"
        
        # Add delivery data from Qdrant results
        for data in relevant_delivery_data:
            context += f"\n--- Dịch vụ giao hàng ---\n"
            if 'id' in data:
                context += f"ID: {data['id']}\n"
            if 'name' in data:
                context += f"Tên dịch vụ: {data['name']}\n"
            if 'delivery_type' in data:
                context += f"Loại dịch vụ: {data['delivery_type']}\n"
            if 'price' in data:
                context += f"Giá: {data['price']} VND\n"
            if 'description' in data:
                context += f"Mô tả: {data['description']}\n"
            if 'service_area' in data:
                context += f"Khu vực phục vụ: {data['service_area']}\n"
        
        # Add delivery details
        for detail in relevant_delivery_details:
            if 'details' in detail and detail['details'] is not None:
                details = detail['details']
                context += f"\n--- Chi tiết giao hàng ---\n"
                
                # Add any additional fields from the details
                for key, value in details.items():
                    if key not in ['id', 'name', 'delivery_type', 'price', 'description', 'service_area', 'score']:
                        context += f"{key}: {value}\n"
        
        # Get system prompt for delivery context
        system_prompt = get_system_prompt_by_context("delivery")
        
        # Add location awareness if location was extracted
        if location:
            location_str = ", ".join([v for k, v in location.items() if v])
            system_prompt += f"\n\nNgười dùng đang hỏi về khu vực: {location_str}. Hãy đảm bảo thông tin trả lời phù hợp với khu vực này nếu có thể."
        
        # Create user prompt with context and question
        prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        
        try:
            # Query OpenAI chat completion
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            answer = response['choices'][0]['message']['content']
            
            return {
                "answer": answer,
                "top_delivery_data": relevant_delivery_data,
                "top_delivery_details": relevant_delivery_details
            }
        except Exception as e:
            logging.error(f"Error querying OpenAI: {e}")
            return {
                "answer": "Xin lỗi, Bé Bơ không thể trả lời câu hỏi của bạn lúc này. Vui lòng thử lại sau hoặc truy cập https://shipperrachgia.vn/ để biết thêm thông tin.",
                "top_delivery_data": [],
                "top_delivery_details": []
            }
