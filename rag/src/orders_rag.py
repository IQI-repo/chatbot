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

class OrdersQdrantManager(QdrantManager):
    """
    Specialized QdrantManager for orders data that uses a different collection name.
    """
    def __init__(self):
        super().__init__()
        self.collection_name = "orders_collection"
        # Ensure collection exists with the new name
        self._create_collection_if_not_exists()
        
    def search_orders(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """
        Search for orders based on a query embedding.
        
        Args:
            query_embedding: Embedding vector for the query
            top_k: Number of top results to return
            
        Returns:
            List of matching orders with their details
        """
        try:
            logging.info(f"Searching for top {top_k} orders")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract order data from search results
            orders = []
            for result in search_result:
                order_data = result.payload
                order_data['score'] = result.score
                orders.append(order_data)
                
            logging.info(f"Found {len(orders)} matching orders")
            return orders
        except Exception as e:
            logging.error(f"Error searching for orders: {e}")
            return []
    
    def search_orders_by_user_id(self, user_id: str, top_k: int = 10) -> List[Dict]:
        """
        Search for orders by user ID.
        
        Args:
            user_id: The user ID to search for
            top_k: Number of top results to return
            
        Returns:
            List of matching orders for the user
        """
        try:
            logging.info(f"Searching for orders by user ID: {user_id}")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_filter={
                    "must": [
                        {
                            "key": "user_id",
                            "match": {
                                "value": user_id
                            }
                        }
                    ]
                },
                limit=top_k
            )
            
            # Extract order data from search results
            orders = []
            for result in search_result:
                order_data = result.payload
                orders.append(order_data)
                
            logging.info(f"Found {len(orders)} orders for user {user_id}")
            return orders
        except Exception as e:
            logging.error(f"Error searching for orders by user ID: {e}")
            return []
    
    def search_orders_by_service_type(self, user_id: str, service_type: str, top_k: int = 5) -> List[Dict]:
        """
        Search for orders by user ID and service type.
        
        Args:
            user_id: The user ID to search for
            service_type: The type of service to search for (restaurant, hotel, taxi, etc.)
            top_k: Number of top results to return
            
        Returns:
            List of matching orders for the user and service type
        """
        try:
            logging.info(f"Searching for {service_type} orders by user ID: {user_id}")
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_filter={
                    "must": [
                        {
                            "key": "user_id",
                            "match": {
                                "value": user_id
                            }
                        },
                        {
                            "key": "type_order_id",
                            "match": {
                                "value": service_type
                            }
                        }
                    ]
                },
                limit=top_k
            )
            
            # Extract order data from search results
            orders = []
            for result in search_result:
                order_data = result.payload
                orders.append(order_data)
                
            logging.info(f"Found {len(orders)} {service_type} orders for user {user_id}")
            return orders
        except Exception as e:
            logging.error(f"Error searching for {service_type} orders by user ID: {e}")
            return []

class OrdersRAG:
    """
    Specialized RAG system for orders data queries.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        logging.debug(f"OpenAI API key loaded: {'Present' if self.api_key else 'Missing'}")
        
        self.processor = TextProcessor()
        self.embeddings_manager = EmbeddingsManager(self.api_key)
        self.qdrant_manager = OrdersQdrantManager()
        
        # Initialize system
        logging.info("Initializing OrdersRAG system")
        self.initialize_system()

    def initialize_system(self):
        """Load orders data and prepare for queries"""
        # Check if data has been loaded into Qdrant
        # For this implementation, we assume data has been loaded using a separate script
        
        logging.info("OrdersRAG system initialized with Qdrant vector database")
        logging.info("If you haven't ingested data yet, please run the ingest_orders_data_to_qdrant.py script")
    
    def search_orders(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for orders based on a query
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of matching orders with their details
        """
        # Get query embedding
        query_embedding = self.embeddings_manager.create_embeddings([query])[0]
        
        # Use Qdrant to find similar orders
        results = self.qdrant_manager.search_orders(query_embedding.tolist(), top_k)
        
        return results
    
    def check_user_service_history(self, user_id: str, service_type: Optional[str] = None) -> Dict:
        """
        Check if a user has used a specific service or any service
        
        Args:
            user_id: The user ID to check
            service_type: Optional service type to check (restaurant, hotel, taxi, etc.)
            
        Returns:
            Dictionary with service usage information
        """
        logging.info(f"Checking service history for user: {user_id}, service_type: {service_type}")
        
        if service_type:
            # Check for specific service type
            orders = self.qdrant_manager.search_orders_by_service_type(user_id, service_type)
            has_used_service = len(orders) > 0
            
            return {
                "user_id": user_id,
                "service_type": service_type,
                "has_used_service": has_used_service,
                "orders": orders
            }
        else:
            # Check for any service
            orders = self.qdrant_manager.search_orders_by_user_id(user_id)
            has_used_service = len(orders) > 0
            
            # Group orders by service type
            service_types = {}
            for order in orders:
                service_type = order.get('type_order_id')
                if service_type not in service_types:
                    service_types[service_type] = []
                service_types[service_type].append(order)
            
            return {
                "user_id": user_id,
                "has_used_any_service": has_used_service,
                "service_types": list(service_types.keys()),
                "service_usage": {k: len(v) for k, v in service_types.items()},
                "orders": orders
            }
    
    def extract_user_info(self, query: str) -> Dict:
        """
        Extract user information from a query using OpenAI
        
        Args:
            query: The user's question about orders
            
        Returns:
            Dictionary with user information if found
        """
        try:
            logging.debug("Extracting user information from query")
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là một trợ lý trích xuất thông tin. Hãy trích xuất thông tin về người dùng từ câu hỏi, bao gồm ID người dùng hoặc tên người dùng nếu có. Nếu không có thông tin về người dùng, hãy trả về 'None'. Nếu có, hãy trả về dưới dạng JSON với các trường: user_id, name_user. Chỉ trả về JSON, không có văn bản giải thích."},
                    {"role": "user", "content": query}
                ]
            )
            
            user_info_text = response['choices'][0]['message']['content']
            
            # If the response is 'None', return None
            if 'None' in user_info_text and len(user_info_text) < 10:
                return None
                
            # Try to parse JSON from the response
            try:
                # Extract JSON from the response if it's embedded in text
                if '{' in user_info_text and '}' in user_info_text:
                    json_start = user_info_text.find('{')
                    json_end = user_info_text.rfind('}') + 1
                    json_str = user_info_text[json_start:json_end]
                    user_info = json.loads(json_str)
                else:
                    user_info = json.loads(user_info_text)
                
                return user_info
            except json.JSONDecodeError:
                logging.error(f"Failed to parse user info JSON: {user_info_text}")
                return None
                
        except Exception as e:
            logging.error(f"Error extracting user info: {e}")
            return None
    
    def extract_service_type(self, query: str) -> str:
        """
        Extract service type from a query using OpenAI
        
        Args:
            query: The user's question about orders
            
        Returns:
            Service type if found, None otherwise
        """
        try:
            logging.debug("Extracting service type from query")
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là một trợ lý trích xuất thông tin. Hãy trích xuất loại dịch vụ từ câu hỏi (nhà hàng, khách sạn, xe ôm, taxi, vé tàu, v.v.). Nếu không có thông tin về loại dịch vụ, hãy trả về 'None'. Chỉ trả về tên loại dịch vụ, không có văn bản giải thích."},
                    {"role": "user", "content": query}
                ]
            )
            
            service_type = response['choices'][0]['message']['content'].strip()
            if service_type.lower() == 'none':
                return None
                
            logging.debug(f"Extracted service type: {service_type}")
            return service_type
        except Exception as e:
            logging.error(f"Error extracting service type: {e}")
            return None
    
    def answer_order_query(self, query: str) -> Dict:
        """
        Answer a query about user's order history
        
        Args:
            query: The user's question about orders
            
        Returns:
            A dictionary containing the answer and relevant order information
        """
        # Extract user information and service type from the query
        user_info = self.extract_user_info(query)
        service_type = self.extract_service_type(query)
        
        if not user_info or 'user_id' not in user_info:
            return {
                "answer": "Xin lỗi, tôi không thể xác định người dùng bạn đang hỏi về. Vui lòng cung cấp thông tin về người dùng.",
                "orders": []
            }
        
        user_id = user_info.get('user_id')
        
        # Check user's service history
        service_history = self.check_user_service_history(user_id, service_type)
        
        # Prepare context
        context = f"Thông tin về lịch sử đặt hàng của người dùng {user_id}:\n\n"
        
        if service_type:
            has_used_service = service_history.get('has_used_service', False)
            context += f"Người dùng {'đã' if has_used_service else 'chưa'} sử dụng dịch vụ {service_type}.\n\n"
        else:
            has_used_any_service = service_history.get('has_used_any_service', False)
            context += f"Người dùng {'đã' if has_used_any_service else 'chưa'} sử dụng bất kỳ dịch vụ nào.\n\n"
            
            if has_used_any_service:
                service_types = service_history.get('service_types', [])
                service_usage = service_history.get('service_usage', {})
                
                context += "Các dịch vụ đã sử dụng:\n"
                for s_type in service_types:
                    context += f"- {s_type}: {service_usage.get(s_type, 0)} lần\n"
                context += "\n"
        
        # Add order details
        orders = service_history.get('orders', [])
        if orders:
            context += "Chi tiết đơn hàng gần đây:\n"
            for i, order in enumerate(orders[:5]):  # Limit to 5 most recent orders
                context += f"\n--- Đơn hàng {i+1} ---\n"
                
                # Add order fields
                for key, value in order.items():
                    if key != 'score':  # Skip the score field
                        context += f"{key}: {value}\n"
        
        # Get system prompt for order context
        system_prompt = get_system_prompt_by_context("order")
        if not system_prompt:
            system_prompt = """Bạn là trợ lý AI giúp trả lời các câu hỏi về lịch sử đặt hàng của người dùng.
            Hãy trả lời dựa trên thông tin được cung cấp về lịch sử đơn hàng của người dùng.
            Nếu người dùng chưa từng sử dụng dịch vụ nào, hãy gợi ý họ thử dịch vụ phù hợp.
            Nếu người dùng đã sử dụng dịch vụ trước đây, hãy nhắc đến các dịch vụ họ đã dùng và gợi ý các dịch vụ tương tự.
            Trả lời bằng tiếng Việt, thân thiện và hữu ích."""
        
        # Create prompt
        prompt = f"""Context: {context}\n\nQuestion: {query}\n\nAnswer:"""
        
        # Get response from OpenAI
        try:
            logging.debug("Sending request to OpenAI for order query")
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract content from response
            answer = response['choices'][0]['message']['content']
            logging.debug(f"Received answer from OpenAI: {answer[:50]}...")
            
            return {
                "answer": answer,
                "user_info": user_info,
                "service_type": service_type,
                "orders": orders
            }
        except Exception as e:
            logging.error(f"Error getting response from OpenAI: {e}")
            return {
                "answer": "Xin lỗi, tôi không thể trả lời câu hỏi của bạn lúc này.",
                "user_info": user_info,
                "service_type": service_type,
                "orders": []
            }
    
    def refresh_orders_data(self):
        """
        Refresh orders data in Qdrant collection.
        This method is called by the scheduler to periodically update the orders data.
        """
        try:
            logging.info("Starting orders data refresh...")
            
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from ingest_orders_data_to_qdrant import ingest_orders_data
            
            # Call the ingestion function
            ingest_orders_data()
            
            logging.info("Orders data refresh completed successfully")
            return True
        except Exception as e:
            logging.error(f"Error refreshing orders data: {e}")
            return False
