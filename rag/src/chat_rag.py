import os
import logging
import json
import uuid
import datetime
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ChatRAG:
    """
    Class for tracking chat history and storing in Qdrant for future querying
    """
    
    def __init__(self):
        """
        Initialize the ChatRAG class with OpenAI API key and Qdrant connection
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logging.warning("OPENAI_API_KEY not found in environment variables")
        else:
            openai.api_key = self.api_key
            logging.info("ChatRAG initialized with OpenAI API key")
        
        # Initialize Qdrant client
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        try:
            self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            logging.info(f"Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            
            # Create collection if it doesn't exist
            self._create_collection_if_not_exists()
        except Exception as e:
            logging.error(f"Error connecting to Qdrant: {str(e)}")
            self.qdrant_client = None
    
    def _create_collection_if_not_exists(self):
        """
        Create the chat history collection in Qdrant if it doesn't exist
        """
        collection_name = "chat_history"
        vector_size = 1536  # OpenAI embeddings dimension
        
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
                logging.info(f"Created collection '{collection_name}' in Qdrant")
                
                # Create payload indexes for efficient filtering
                self.qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="timestamp",
                    field_schema="datetime"
                )
                
                self.qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="user_id",
                    field_schema="keyword"
                )
                
                self.qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name="session_id",
                    field_schema="keyword"
                )
                
                logging.info("Created payload indexes for chat history collection")
            else:
                logging.info(f"Collection '{collection_name}' already exists in Qdrant")
        
        except Exception as e:
            logging.error(f"Error creating collection: {str(e)}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using OpenAI API
        
        Args:
            text: The text to get embedding for
            
        Returns:
            List of floats representing the embedding
        """
        try:
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002"
            )
            embedding = response['data'][0]['embedding']
            return embedding
        except Exception as e:
            logging.error(f"Error getting embedding: {str(e)}")
            # Return a zero vector as fallback
            return [0.0] * 1536
    
    def store_chat_interaction(self, 
                              user_id: str, 
                              question: str, 
                              answer: str, 
                              context_type: str,
                              session_id: Optional[str] = None) -> bool:
        """
        Store a chat interaction in Qdrant
        
        Args:
            user_id: Identifier for the user
            question: User's question
            answer: System's answer
            context_type: Type of context (restaurant, hotel, delivery, etc.)
            session_id: Optional session identifier
            
        Returns:
            Boolean indicating success or failure
        """
        if not self.qdrant_client:
            logging.error("Qdrant client not initialized")
            return False
        
        try:
            # Generate a session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Get embedding for the question
            question_embedding = self._get_embedding(question)
            
            # Create timestamp
            timestamp = datetime.datetime.now().isoformat()
            
            # Create point ID
            point_id = str(uuid.uuid4())
            
            # Store in Qdrant
            self.qdrant_client.upsert(
                collection_name="chat_history",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=question_embedding,
                        payload={
                            "user_id": user_id,
                            "session_id": session_id,
                            "question": question,
                            "answer": answer,
                            "context_type": context_type,
                            "timestamp": timestamp
                        }
                    )
                ]
            )
            
            logging.info(f"Stored chat interaction for user {user_id} with ID {point_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error storing chat interaction: {str(e)}")
            return False
    
    def search_similar_questions(self, 
                                question: str, 
                                limit: int = 5, 
                                user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar questions in the chat history
        
        Args:
            question: The question to search for
            limit: Maximum number of results to return
            user_id: Optional user ID to filter by
            
        Returns:
            List of dictionaries containing similar questions and their answers
        """
        if not self.qdrant_client:
            logging.error("Qdrant client not initialized")
            return []
        
        try:
            # Get embedding for the question
            question_embedding = self._get_embedding(question)
            
            # Prepare search filters
            search_params = {
                "collection_name": "chat_history",
                "query_vector": question_embedding,
                "limit": limit
            }
            
            # Add user filter if provided
            if user_id:
                search_params["query_filter"] = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                )
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(**search_params)
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "question": result.payload.get("question"),
                    "answer": result.payload.get("answer"),
                    "context_type": result.payload.get("context_type"),
                    "timestamp": result.payload.get("timestamp"),
                    "similarity_score": result.score
                })
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error searching similar questions: {str(e)}")
            return []
    
    def get_user_chat_history(self, 
                             user_id: str, 
                             limit: int = 10, 
                             session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific user
        
        Args:
            user_id: User ID to get history for
            limit: Maximum number of results to return
            session_id: Optional session ID to filter by
            
        Returns:
            List of dictionaries containing chat history
        """
        if not self.qdrant_client:
            logging.error("Qdrant client not initialized")
            return []
        
        try:
            # Prepare filters
            filter_conditions = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
            
            # Add session filter if provided
            if session_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="session_id",
                        match=models.MatchValue(value=session_id)
                    )
                )
            
            # Search in Qdrant
            search_results = self.qdrant_client.scroll(
                collection_name="chat_history",
                scroll_filter=models.Filter(
                    must=filter_conditions
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            formatted_results = []
            for point in search_results[0]:
                formatted_results.append({
                    "question": point.payload.get("question"),
                    "answer": point.payload.get("answer"),
                    "context_type": point.payload.get("context_type"),
                    "timestamp": point.payload.get("timestamp")
                })
            
            # Sort by timestamp
            formatted_results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error getting user chat history: {str(e)}")
            return []
    
    def get_popular_questions(self, 
                             limit: int = 10, 
                             days: int = 7) -> List[Dict[str, Any]]:
        """
        Get most popular questions based on similarity clustering
        
        Args:
            limit: Maximum number of results to return
            days: Number of days to look back
            
        Returns:
            List of dictionaries containing popular questions
        """
        if not self.qdrant_client:
            logging.error("Qdrant client not initialized")
            return []
        
        try:
            # Calculate date threshold
            date_threshold = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            # Get recent questions
            search_results = self.qdrant_client.scroll(
                collection_name="chat_history",
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="timestamp",
                            range=models.Range(
                                gt=date_threshold
                            )
                        )
                    ]
                ),
                limit=1000,  # Get a large sample to analyze
                with_payload=True,
                with_vectors=True
            )
            
            # Not enough data for clustering
            if not search_results[0]:
                return []
            
            # Simple frequency-based approach (can be enhanced with proper clustering)
            question_counts = {}
            for point in search_results[0]:
                question = point.payload.get("question", "").lower()
                if question in question_counts:
                    question_counts[question]["count"] += 1
                else:
                    question_counts[question] = {
                        "count": 1,
                        "original_question": point.payload.get("question"),
                        "context_type": point.payload.get("context_type"),
                        "last_answer": point.payload.get("answer")
                    }
            
            # Sort by frequency
            popular_questions = sorted(
                [{"question": v["original_question"], 
                  "count": v["count"], 
                  "context_type": v["context_type"],
                  "last_answer": v["last_answer"]} 
                 for k, v in question_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )
            
            return popular_questions[:limit]
            
        except Exception as e:
            logging.error(f"Error getting popular questions: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    chat_rag = ChatRAG()
    
    # Store a sample interaction
    chat_rag.store_chat_interaction(
        user_id="user123",
        question="Nhà hàng nào ngon nhất ở Rạch Giá?",
        answer="Xin chào! Em là Bé Bơ. Theo đánh giá gần đây, nhà hàng ABC được đánh giá cao về hải sản tươi ngon tại Rạch Giá.",
        context_type="restaurant"
    )
    
    # Search for similar questions
    similar = chat_rag.search_similar_questions("Quán ăn nào ngon ở Rạch Giá?")
    print(f"Found {len(similar)} similar questions")
