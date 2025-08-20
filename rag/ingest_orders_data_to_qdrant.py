import os
import json
import logging
import time
from dotenv import load_dotenv
import numpy as np
from typing import List, Dict, Any
import pandas as pd
import mysql.connector
from datetime import datetime

from src.embeddings_manager import EmbeddingsManager
from src.qdrant_manager import QdrantManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrdersQdrantManager(QdrantManager):
    """
    Specialized QdrantManager for orders data that uses a different collection name.
    """
    def __init__(self):
        super().__init__()
        self.collection_name = "orders_collection"
        # Ensure collection exists with the new name
        self._create_collection_if_not_exists()

class OrdersDataIngester:
    """
    Class to ingest orders data into Qdrant.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        self.embeddings_manager = EmbeddingsManager(self.api_key)
        self.qdrant_manager = OrdersQdrantManager()
        
        logger.info("Orders Data Ingester initialized")
    
    def prepare_order_data(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare order data for ingestion by creating a text representation
        and extracting relevant fields.
        
        Args:
            order: Raw order data
            
        Returns:
            Processed order data ready for embedding
        """
        # Create a text representation of the order for embedding
        order_text = f"Order ID: {order.get('id', 'Unknown')}\n"
        
        # Add user information
        order_text += f"User ID: {order.get('user_id', 'Unknown')}\n"
        if 'user_name' in order and order['user_name']:
            order_text += f"User Name: {order.get('user_name')}\n"
        if 'user_phone' in order and order['user_phone']:
            order_text += f"User Phone: {order.get('user_phone')}\n"
        if 'user_email' in order and order['user_email']:
            order_text += f"User Email: {order.get('user_email')}\n"
        
        # Add service type information
        if 'service_type' in order:
            order_text += f"Service Type: {order.get('service_type')}\n"
        else:
            order_text += f"Order Type ID: {order.get('type_order_id', 'Unknown')}\n"
        
        # Add status information
        if 'status' in order:
            order_text += f"Status: {order.get('status')}\n"
        else:
            order_text += f"Status ID: {order.get('orderstatus_id', 'Unknown')}\n"
        
        # Add payment information
        order_text += f"Payment Method: {order.get('payment_method_code', 'Unknown')}\n"
        
        # Add location information if available
        if 'latitude' in order and 'longitude' in order and order['latitude'] and order['longitude']:
            order_text += f"Location: {order.get('latitude')}, {order.get('longitude')}\n"
        
        # Add address if available
        if 'address' in order and order['address']:
            order_text += f"Address: {order.get('address')}\n"
        
        # Add pricing information
        if 'total' in order and order['total']:
            order_text += f"Total: {order.get('total')}\n"
        
        # Add date information
        if 'created_at' in order and order['created_at']:
            order_text += f"Created At: {order.get('created_at')}\n"
        if 'updated_at' in order and order['updated_at']:
            order_text += f"Updated At: {order.get('updated_at')}\n"
        
        # Add any additional fields that might be useful for searching
        important_fields = ['promo_restaurant_code', 'distance', 'delivery_charge', 
                           'total_discount', 'note', 'phone', 'flash_detail_buy', 
                           'reason_cancel', 'point_delivery_id', 'area']
        
        for field in important_fields:
            if field in order and order[field]:
                order_text += f"{field.replace('_', ' ').title()}: {order[field]}\n"
        
        # Return the processed order with text representation
        return {
            "id": order.get('id'),
            "text_representation": order_text,
            **order  # Include all original fields
        }
    
    def create_embeddings_for_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create embeddings for a list of orders.
        
        Args:
            orders: List of processed order data
            
        Returns:
            List of orders with embeddings
        """
        logger.info(f"Creating embeddings for {len(orders)} orders")
        
        # Extract text representations for embedding
        texts = [order["text_representation"] for order in orders]
        
        # Create embeddings in batches to avoid API limits
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            batch_embeddings = self.embeddings_manager.create_embeddings(batch_texts)
            all_embeddings.extend(batch_embeddings)
        
        # Add embeddings to order data
        for i, order in enumerate(orders):
            order["embedding"] = all_embeddings[i].tolist()
        
        return orders
    
    def ingest_orders_to_qdrant(self, orders_with_embeddings: List[Dict[str, Any]]) -> None:
        """
        Ingest orders with embeddings into Qdrant.
        
        Args:
            orders_with_embeddings: List of orders with embeddings
        """
        logger.info(f"Ingesting {len(orders_with_embeddings)} orders into Qdrant")
        
        # Prepare points for Qdrant
        points = []
        for order in orders_with_embeddings:
            # Create a copy of the order without the embedding and text_representation
            payload = {k: v for k, v in order.items() if k not in ["embedding", "text_representation"]}
            
            # Add the point - ensure ID is an integer
            try:
                # Convert ID to integer
                point_id = int(order["id"])
            except (ValueError, TypeError):
                # If conversion fails, use a hash of the ID as fallback
                import hashlib
                point_id = int(hashlib.md5(str(order["id"]).encode()).hexdigest(), 16) % (10 ** 10)
                logger.warning(f"Converted non-integer ID '{order['id']}' to integer hash {point_id}")
                
            points.append({
                "id": point_id,
                "vector": order["embedding"],
                "payload": payload
            })
        
        # Upload points to Qdrant in smaller batches to avoid timeouts
        batch_size = 20  # Reduced batch size for more reliable uploads
        for i in range(0, len(points), batch_size):
            batch_points = points[i:i+batch_size]
            logger.info(f"Uploading batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")
            
            # Add retry logic for uploading points
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    self.qdrant_manager.client.upsert(
                        collection_name=self.qdrant_manager.collection_name,
                        points=batch_points
                    )
                    success = True
                    logger.info(f"Successfully uploaded batch {i//batch_size + 1}")
                except Exception as e:
                    retry_count += 1
                    wait_time = 2 ** retry_count
                    logger.warning(f"Error uploading batch {i//batch_size + 1}: {e}. Retry {retry_count}/{max_retries} in {wait_time} seconds...")
                    time.sleep(wait_time)
            
            if not success:
                logger.error(f"Failed to upload batch {i//batch_size + 1} after {max_retries} attempts")
                # Continue with next batch instead of failing completely
        
        logger.info(f"Successfully ingested {len(orders_with_embeddings)} orders into Qdrant")
    
    def load_orders_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load orders data from a CSV file.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of order data
        """
        logger.info(f"Loading orders from CSV: {csv_path}")
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Convert DataFrame to list of dictionaries
            orders = df.to_dict(orient='records')
            
            logger.info(f"Loaded {len(orders)} orders from CSV")
            return orders
        except Exception as e:
            logger.error(f"Error loading orders from CSV: {e}")
            return []
    
    def load_orders_from_json(self, json_path: str) -> List[Dict[str, Any]]:
        """
        Load orders data from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            List of order data
        """
        logger.info(f"Loading orders from JSON: {json_path}")
        
        try:
            # Read JSON file
            with open(json_path, 'r', encoding='utf-8') as f:
                orders = json.load(f)
                
            logger.info(f"Loaded {len(orders)} orders from JSON")
            return orders
        except Exception as e:
            logger.error(f"Error loading orders from JSON: {e}")
            return []
    
    def fetch_orders_from_mysql(self) -> List[Dict[str, Any]]:
        """
        Fetch orders data directly from MySQL database.
        
        Returns:
            List of order data
        """
        logger.info("Fetching orders from MySQL database")
        
        # Load database configuration from environment variables
        db_config = {
            'host': os.getenv('MYSQL_DB_HOST'),
            'port': int(os.getenv('MYSQL_DB_PORT', 3306)),
            'user': os.getenv('MYSQL_DB_USERNAME'),
            'password': os.getenv('MYSQL_DB_PASSWORD'),
            'database': os.getenv('MYSQL_DB_NAME', 'boship')
        }
        
        try:
            # Connect to the database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Fetch all orders with user information
            cursor.execute("""
                SELECT o.*, u.name as user_name, u.phone as user_phone, u.email as user_email
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                ORDER BY o.created_at DESC
            """)
            orders = cursor.fetchall()
            
            # Process each order to get additional information if needed
            for order in orders:
                # Add service type information based on type_order_id
                # 1: Restaurant, 2: Hotel, 3: Taxi, etc.
                type_id = order.get('type_order_id')
                if type_id == 1:
                    order['service_type'] = 'Restaurant'
                elif type_id == 2:
                    order['service_type'] = 'Hotel'
                elif type_id == 3:
                    order['service_type'] = 'Taxi'
                else:
                    order['service_type'] = f'Service type {type_id}'
                
                # Add status information
                status_id = order.get('orderstatus_id')
                if status_id == 1:
                    order['status'] = 'Pending'
                elif status_id == 2:
                    order['status'] = 'Confirmed'
                elif status_id == 3:
                    order['status'] = 'Completed'
                elif status_id == 4:
                    order['status'] = 'Cancelled'
                else:
                    order['status'] = f'Status {status_id}'
            
            # Convert datetime objects to strings for JSON serialization
            for order in orders:
                for key, value in order.items():
                    if isinstance(value, datetime):
                        order[key] = value.isoformat()
            
            logger.info(f"Fetched {len(orders)} orders from MySQL database")
            
            # Close database connection
            cursor.close()
            conn.close()
            
            return orders
        except Exception as e:
            logger.error(f"Error fetching orders from MySQL: {e}")
            return []
            
    
    def process_and_ingest_orders(self, orders: List[Dict[str, Any]]) -> None:
        """
        Process and ingest orders into Qdrant.
        
        Args:
            orders: List of raw order data
        """
        # Prepare order data
        processed_orders = [self.prepare_order_data(order) for order in orders]
        
        # Create embeddings
        orders_with_embeddings = self.create_embeddings_for_orders(processed_orders)
        
        # Ingest into Qdrant
        self.ingest_orders_to_qdrant(orders_with_embeddings)

def main():
    """
    Main function to ingest orders data into Qdrant.
    """
    # Initialize ingester
    ingester = OrdersDataIngester()
    
    # Try to fetch orders from MySQL first
    orders = ingester.fetch_orders_from_mysql()
    
    # If MySQL fetch fails, try local files as fallback
    if not orders:
        logger.warning("Failed to fetch orders from MySQL, trying local files as fallback")
        
        # Define data paths
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        orders_json_path = os.path.join(data_dir, 'orders.json')
        orders_csv_path = os.path.join(data_dir, 'orders.csv')
        
        # Load orders from JSON or CSV
        if os.path.exists(orders_json_path):
            orders = ingester.load_orders_from_json(orders_json_path)
        elif os.path.exists(orders_csv_path):
            orders = ingester.load_orders_from_csv(orders_csv_path)
        else:
            logger.error(f"No orders data found at {orders_json_path} or {orders_csv_path}")
            return
    
    # Process and ingest orders
    if orders:
        logger.info(f"Processing and ingesting {len(orders)} orders")
        ingester.process_and_ingest_orders(orders)
        logger.info("Orders ingestion completed successfully")
    else:
        logger.error("No orders data to ingest")

if __name__ == "__main__":
    main()
