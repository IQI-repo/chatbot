from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.restaurant_rag import RestaurantRAG
from src.hotel_rag import HotelRAG
from src.delivery_rag import DeliveryRAG
from src.context_detector import ContextDetector
from src.system_prompt import get_system_prompt_by_context
from src.web_search import WebSearch
from src.chat_rag import ChatRAG
from src.scheduler import RagScheduler
import uvicorn
import logging
import traceback
import os
import mysql.connector
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Database connection configuration
DB_CONFIG = {
    'host': '103.116.9.57',
    'port': 3306,
    'user': 'boship',
    'password': 'Admin@1234',
    'database': 'boship'  # Default database name, replace if needed
}

# Function to get database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.info("Database connection established successfully")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        raise

# Initialize the RAG systems
restaurant_rag = RestaurantRAG()
hotel_rag = HotelRAG()
delivery_rag = DeliveryRAG()
context_detector = ContextDetector()
web_search = WebSearch()
chat_rag = ChatRAG()

# Initialize and start the scheduler
scheduler = RagScheduler(refresh_interval_minutes=10)
scheduler.start()

# Create FastAPI app
app = FastAPI(
    title="Unified RAG API",
    description="API for querying multiple services using context detection and RAG",
    version="1.0.0"
)

class Query(BaseModel):
    question: str
    user_id: str = "anonymous"
    session_id: str = None

class RestaurantResponse(BaseModel):
    answer: str
    top_restaurants: list
    top_menu_items: list

class HotelResponse(BaseModel):
    answer: str
    top_hotels: list
    top_rooms: list

class UnifiedParent(BaseModel):
    id: str
    name: str

class UnifiedChild(BaseModel):
    id: str
    name: str
    parentId: str

class UnifiedResponse(BaseModel):
    answer: str
    service_name: str
    top_parents: list[UnifiedParent]
    top_childs: list[UnifiedChild]

@app.post("/api/restaurant-query", response_model=RestaurantResponse)
async def restaurant_query(query: Query):
    """
    Endpoint to query restaurant information
    
    Args:
        query: The question about restaurants or food
        
    Returns:
        Response with answer, top matching restaurants and menu items
    """
    try:
        logging.info(f"Received query: {query.question}")
        
        # Get answer from RAG system
        logging.debug("Calling answer_restaurant_query")
        answer = restaurant_rag.answer_restaurant_query(query.question)
        logging.debug(f"Got answer: {answer[:50]}...")
        
        # Store the interaction in chat history
        chat_rag.store_chat_interaction(
            user_id=query.user_id,
            question=query.question,
            answer=answer,
            context_type="restaurant",
            session_id=query.session_id
        )
        
        # Get top matching restaurants
        logging.debug("Calling search_restaurants")
        top_restaurants = restaurant_rag.search_restaurants(query.question, top_k=2)
        logging.debug(f"Got {len(top_restaurants)} restaurants")
        
        restaurant_results = []
        for i, restaurant in enumerate(top_restaurants):
            logging.debug(f"Processing restaurant {i}: {restaurant}")
            try:
                # Handle Qdrant response format
                name = restaurant.get('name', 'Unknown')
                address = restaurant.get('address', 'No address')
                restaurant_results.append(f"{name} ({address})")
                logging.debug(f"Added restaurant: {name}")
            except KeyError as ke:
                logging.error(f"KeyError in restaurant data: {ke}, restaurant data: {restaurant}")
                raise
        
        # Get top matching menu items
        logging.debug("Calling search_menu_items")
        top_items = restaurant_rag.search_menu_items(query.question, top_k=3)
        logging.debug(f"Got {len(top_items)} menu items")
        
        item_results = []
        for i, item in enumerate(top_items):
            logging.debug(f"Processing menu item {i}: {item}")
            try:
                # Handle Qdrant response format
                item_data = item.get('item', {})
                item_name = item_data.get('name', 'Unknown')
                item_price = item_data.get('price', 0)
                restaurant_name = item.get('restaurant_name', 'Unknown restaurant')
                
                item_results.append(f"{item_name} - {item_price} VND at {restaurant_name}")
                logging.debug(f"Added menu item: {item_name}")
            except KeyError as ke:
                logging.error(f"KeyError in menu item data: {ke}, item data: {item}")
                raise
        
        logging.info("Successfully processed query, returning response")
        return RestaurantResponse(
            answer=answer,
            top_restaurants=restaurant_results,
            top_menu_items=item_results
        )
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint that returns API information"""
    return {
        "message": "Restaurant RAG API is running",
        "usage": "Send POST requests to /api/restaurant-query with a JSON body containing 'question'"
    }

@app.post("/api/hotel-query", response_model=HotelResponse)
async def hotel_query(query: Query):
    """
    Endpoint to query hotel information
    
    Args:
        query: The question about hotels
        
    Returns:
        Response with answer, top matching hotels and rooms
    """
    try:
        logging.info(f"Received hotel query: {query.question}")
        
        # Get answer from Hotel RAG system
        logging.debug("Calling answer_hotel_query")
        result = hotel_rag.answer_hotel_query(query.question)
        answer = result["answer"]
        logging.debug(f"Got answer: {answer[:50]}...")
        
        # Get top matching hotels from the result
        top_hotels = result["top_hotels"]
        logging.debug(f"Got {len(top_hotels)} hotels")
        
        # Process hotel results to match restaurant format
        hotel_results = []
        for i, hotel in enumerate(top_hotels):
            logging.debug(f"Processing hotel {i}: {hotel}")
            try:
                # Format hotel data consistently
                name = hotel.get('name', 'Unknown')
                address = hotel.get('address', 'No address')
                hotel_results.append(f"{name} ({address})")
                logging.debug(f"Added hotel: {name}")
            except KeyError as ke:
                logging.error(f"KeyError in hotel data: {ke}, hotel data: {hotel}")
                raise
        
        # Get top matching rooms from the result
        top_rooms = result["top_rooms"]
        logging.debug(f"Got {len(top_rooms)} rooms")
        
        # Process room results to match menu item format
        room_results = []
        for i, room_info in enumerate(top_rooms):
            logging.debug(f"Processing room {i}: {room_info}")
            try:
                # Format room data consistently
                room = room_info.get('room', {})
                room_name = room.get('name', 'Unknown')
                room_price = room.get('price', 0)
                hotel_name = room_info.get('hotel_name', 'Unknown hotel')
                
                room_results.append(f"{room_name} - {room_price} VND at {hotel_name}")
                logging.debug(f"Added room: {room_name}")
            except KeyError as ke:
                logging.error(f"KeyError in room data: {ke}, room data: {room_info}")
                raise
        
        logging.info("Successfully processed hotel query, returning response")
        return HotelResponse(
            answer=answer,
            top_hotels=hotel_results,
            top_rooms=room_results
        )
    except Exception as e:
        logging.error(f"Error processing hotel query: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chatbot-query", response_model=UnifiedResponse)
async def unified_query(query: Query):
    """
    Unified endpoint to query all services based on context detection
    
    Args:
        query: The user's question
        
    Returns:
        Response with answer, service name, and top matching items in a unified format
    """
    try:
        logging.info(f"Received unified query: {query.question}")
        
        if not query.question.strip():
            logging.info("Received empty question, sending welcome message")
            return UnifiedResponse(
                answer="Xin chào anh/chị! Em là Bé Bơ đây ạ! ❤️\n\nEm là nhân viên tư vấn của ShipperRachGia.vn, em có thể giúp anh/chị tìm hiểu về:\n- Nhà hàng và món ăn ngon tại Rạch Giá\n- Khách sạn và dịch vụ lưu trú\n- Dịch vụ giao hàng và vận chuyển\n\nAnh/chị có thể hỏi em bất cứ điều gì về các dịch vụ của ShipperRachGia.vn!\n\nDạ để được nhận nhiều Ưu Đãi và Khuyến Mãi A/C vui lòng nhắn vào đây giúp Bé Bơ ạ https://zalo.me/4018474138015540620 Hoặc gọi: 1900585878 - 0939785878. Giúp em nha!",
                service_name="welcome",
                top_parents=[],
                top_childs=[]
            )
        
        # Step 1: Detect the context of the query
        context_result = context_detector.detect_context(query.question)
        primary_context = context_result["primary_context"]
        confidence = context_result["confidence"]
        
        logging.info(f"Detected context: {primary_context} with confidence {confidence:.2f}")
        
        # Step 2: Route to appropriate service based on context
        if primary_context == "restaurant":
            service_name = "restaurant"
            # Get answer from Restaurant RAG system
            raw_answer = restaurant_rag.answer_restaurant_query(query.question)
            # Format as Vietnamese response from Bé Bơ
            answer = f"Xin chào anh/chị! Em là Bé Bơ đây ạ! ❤️\n\n{raw_answer}\n\nDạ để được nhận nhiều Ưu Đãi và Khuyến Mãi A/C vui lòng nhắn vào đây giúp Bé Bơ ạ https://zalo.me/4018474138015540620 Hoặc gọi: 1900585878 - 0939785878. Giúp em nha!"
            
            # Get top matching restaurants
            top_restaurants = restaurant_rag.search_restaurants(query.question, top_k=3)
            
            # Get top matching menu items
            top_items = restaurant_rag.search_menu_items(query.question, top_k=3)
            
            # Format as unified response
            top_parents = []
            for restaurant in top_restaurants:
                restaurant_id = restaurant.get('id', 'unknown')
                name = restaurant.get('name', 'Unknown')
                top_parents.append(UnifiedParent(id=str(restaurant_id), name=name))
            
            top_childs = []
            for item in top_items:
                item_data = item.get('item', {})
                item_id = item_data.get('id', 'unknown')
                item_name = item_data.get('name', 'Unknown')
                restaurant_id = item.get('restaurant_id', 'unknown')
                top_childs.append(UnifiedChild(id=str(item_id), name=item_name, parentId=str(restaurant_id)))
            
        elif primary_context == "accommodation":
            service_name = "hotel"
            # Get answer from Hotel RAG system
            logging.debug("Calling answer_hotel_query")
            result = hotel_rag.answer_hotel_query(query.question)
            raw_answer = result["answer"]
            # Format as Vietnamese response from Bé Bơ
            answer = f"Xin chào anh/chị! Em là Bé Bơ đây ạ! ❤️\n\n{raw_answer}\n\nDạ để được nhận nhiều Ưu Đãi và Khuyến Mãi A/C vui lòng nhắn vào đây giúp Bé Bơ ạ https://zalo.me/4018474138015540620 Hoặc gọi: 1900585878 - 0939785878. Giúp em nha!"
            
            # Store the interaction in chat history
            chat_rag.store_chat_interaction(
                user_id=query.user_id,
                question=query.question,
                answer=answer,
                context_type="hotel",
                session_id=query.session_id
            )
            
            # Get top matching hotels
            top_hotels = result["top_hotels"]
            
            # Get top matching rooms
            top_rooms = result["top_rooms"]
            
            # Format as unified response
            top_parents = []
            for hotel in top_hotels:
                hotel_id = hotel.get('id', 'unknown')
                name = hotel.get('name', 'Unknown')
                top_parents.append(UnifiedParent(id=str(hotel_id), name=name))
            
            top_childs = []
            for room_info in top_rooms:
                room = room_info.get('room', {})
                room_id = room.get('id', 'unknown')
                room_name = room.get('name', 'Unknown')
                hotel_id = room_info.get('hotel_id', 'unknown')
                top_childs.append(UnifiedChild(id=str(room_id), name=room_name, parentId=str(hotel_id)))
                
        elif primary_context == "delivery":
            service_name = "delivery"
            # Get answer from Delivery RAG system
            result = delivery_rag.answer_delivery_query(query.question)
            raw_answer = result["answer"]
            # Format as Vietnamese response from Bé Bơ
            answer = f"Xin chào anh/chị! Em là Bé Bơ đây ạ! ❤️\n\n{raw_answer}\n\nDạ để được nhận nhiều Ưu Đãi và Khuyến Mãi A/C vui lòng nhắn vào đây giúp Bé Bơ ạ https://zalo.me/4018474138015540620 Hoặc gọi: 1900585878 - 0939785878. Giúp em nha!"
            
            # Store the interaction in chat history
            chat_rag.store_chat_interaction(
                user_id=query.user_id,
                question=query.question,
                answer=answer,
                context_type="delivery",
                session_id=query.session_id
            )
            
            # Get top matching delivery data
            top_delivery_data = result["top_delivery_data"]
            
            # Get top matching delivery details
            top_delivery_details = result["top_delivery_details"]
            
            # Format as unified response
            top_parents = []
            for delivery in top_delivery_data:
                delivery_id = delivery.get('id', 'unknown')
                name = delivery.get('name', 'Unknown')
                top_parents.append(UnifiedParent(id=str(delivery_id), name=name))
            
            top_childs = []
            for detail in top_delivery_details:
                detail_id = detail.get('delivery_id', 'unknown')
                detail_name = detail.get('delivery_type', 'Unknown')
                delivery_id = detail.get('delivery_id', 'unknown')
                top_childs.append(UnifiedChild(id=str(detail_id), name=detail_name, parentId=str(delivery_id)))
            
        else:
            # For contexts we don't have specific handlers for yet
            service_name = primary_context
            
            logging.info(f"No specific handler for context {primary_context}, trying web search")
            search_result = web_search.search_web(query.question)
            
            if search_result["success"]:
                # If web search was successful, use the formatted answer
                answer = search_result["answer"]
                logging.info("Web search successful, using search results")
            else:
                # Before giving up, check if we have similar questions in chat history
                similar_questions = chat_rag.search_similar_questions(query.question, limit=1)
                
                if similar_questions and similar_questions[0]["similarity_score"] > 0.85:
                    # Use the answer from a similar question if it's very similar
                    answer = similar_questions[0]["answer"]
                    logging.info(f"Using answer from similar question with score {similar_questions[0]['similarity_score']}")
                else:
                    # If web search failed and no similar questions, use the default fallback response
                    answer = f"Xin chào anh/chị! Em là Bé Bơ đây ạ! ❤️\n\nEm chưa có thông tin cụ thể về dịch vụ này. Anh/chị có thể chia sẻ thêm về điều anh/chị đang tìm kiếm được không ạ? Em rất muốn được giúp anh/chị tốt hơn!\n\nTrong lúc đó, anh/chị có thể tham khảo thêm thông tin tại website https://shipperrachgia.vn/ nha!\n\nDạ để được nhận nhiều Ưu Đãi và Khuyến Mãi A/C vui lòng nhắn vào đây giúp Bé Bơ ạ https://zalo.me/4018474138015540620 Hoặc gọi: 1900585878 - 0939785878. Giúp em nha!"
                    logging.warning(f"Web search failed: {search_result['answer']}")
            
            # Store the interaction in chat history
            chat_rag.store_chat_interaction(
                user_id=query.user_id,
                question=query.question,
                answer=answer,
                context_type=service_name,
                session_id=query.session_id
            )
            
            top_parents = []
            top_childs = []
        
        logging.info(f"Successfully processed unified query for {service_name}, returning response")
        return UnifiedResponse(
            answer=answer,
            service_name=service_name,
            top_parents=top_parents,
            top_childs=top_childs
        )
        
    except Exception as e:
        logging.error(f"Error processing unified query: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing unified query: {str(e)}")


# Add shutdown event to stop the scheduler when the API stops
@app.on_event("shutdown")
def shutdown_event():
    logging.info("Shutting down scheduler...")
    scheduler.stop()
    logging.info("Scheduler stopped")

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
