from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.restaurant_rag import RestaurantRAG
import uvicorn
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize the RestaurantRAG system
rag = RestaurantRAG()

# Create FastAPI app
app = FastAPI(
    title="Restaurant RAG API",
    description="API for querying restaurant information using RAG",
    version="1.0.0"
)

class Query(BaseModel):
    question: str

class Response(BaseModel):
    answer: str
    top_restaurants: list
    top_menu_items: list

@app.post("/api/restaurant-query", response_model=Response)
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
        answer = rag.answer_restaurant_query(query.question)
        logging.debug(f"Got answer: {answer[:50]}...")
        
        # Get top matching restaurants
        logging.debug("Calling search_restaurants")
        top_restaurants = rag.search_restaurants(query.question, top_k=2)
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
        top_items = rag.search_menu_items(query.question, top_k=3)
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
        return Response(
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

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
