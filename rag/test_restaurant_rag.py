from src.restaurant_rag import RestaurantRAG

def main():
    # Initialize the Restaurant RAG system
    print("Initializing Restaurant RAG system...")
    rag = RestaurantRAG()
    
    # Test with some sample queries
    test_queries = [
        "Tìm nhà hàng bán trà sữa",
        "Món ăn nào có giá dưới 50000 VND?",
        "Nhà hàng nào bán gà?",
        "Tôi muốn ăn ốc, có nhà hàng nào không?",
        "Có món hải sản nào không?"
    ]
    
    for query in test_queries:
        print("\n" + "="*50)
        print(f"Query: {query}")
        print("="*50)
        
        # Get answer
        answer = rag.answer_restaurant_query(query)
        print(f"Answer: {answer}")
        
        # Show top restaurants
        print("\nTop matching restaurants:")
        restaurants = rag.search_restaurants(query, top_k=2)
        for restaurant in restaurants:
            print(f"- {restaurant.get('name')} ({restaurant.get('address')})")
        
        # Show top menu items
        print("\nTop matching menu items:")
        menu_items = rag.search_menu_items(query, top_k=3)
        for item_info in menu_items:
            item = item_info['item']
            print(f"- {item.get('name')} - {item.get('price')} VND at {item_info['restaurant_name']}")

if __name__ == "__main__":
    main()
