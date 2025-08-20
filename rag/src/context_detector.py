import os
import logging
import openai
from typing import Dict, List, Any, Optional

class ContextDetector:
    """
    A class to detect the context of user queries using OpenAI.
    This helps identify which service the user is referring to (food, accommodation, driver, etc.)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the context detector with OpenAI API key.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from environment variable.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logging.error("OpenAI API key not found. Context detection will not work.")
        else:
            # For OpenAI 0.28.1, we just set the API key
            openai.api_key = self.api_key
            logging.info("OpenAI API key set successfully for context detection")
    
    def detect_context(self, query: str) -> Dict[str, Any]:
        """
        Detect the context of a user query to identify which service they are referring to.
        
        Args:
            query: The user's query text
            
        Returns:
            A dictionary containing:
                - primary_context: The main service context detected
                - confidence: Confidence score (0-1)
                - all_contexts: Dictionary of all possible contexts with their scores
        """
        try:
            logging.debug(f"Detecting context for query: {query}")
            
            # Define the prompt for context detection
            system_prompt = """
            Bạn là nhân viên tư vấn Bé Bơ, phụ trách phân loại câu hỏi của người dùng. Nhiệm vụ của bạn là xác định câu hỏi thuộc danh mục dịch vụ nào.
            Phân tích câu hỏi và xác định nó thuộc vào một trong các ngữ cảnh sau:
            
            1. restaurant - Câu hỏi về đồ ăn, ăn uống, nhà hàng, thực đơn, món ăn, ẩm thực, v.v.
            2. accommodation - Câu hỏi về khách sạn, phòng ở, lưu trú, tiện nghi, v.v.
            3. delivery - Câu hỏi về dịch vụ giao hàng, vận chuyển hàng hóa, đơn hàng, theo dõi giao hàng, v.v.
            4. transportation - Câu hỏi về di chuyển, đi lại, tài xế, phương tiện, v.v.
            5. tourism - Câu hỏi về điểm tham quan, thắng cảnh, tour du lịch, v.v.
            6. order - Câu hỏi về lịch sử đặt hàng, đơn hàng đã đặt, dịch vụ đã sử dụng, v.v.
            7. general - Câu hỏi chung không thuộc các danh mục trên
            
            Trả lời của bạn phải là một đối tượng JSON với cấu trúc sau:
            {
                "primary_context": "[Danh mục chính - phải là một trong các giá trị: restaurant, accommodation, delivery, transportation, tourism, order, general]",
                "confidence": [Một số từ 0 đến 1 chỉ mức độ tin cậy],
                "all_contexts": {
                    "restaurant": [Điểm từ 0 đến 1],
                    "accommodation": [Điểm từ 0 đến 1],
                    "delivery": [Điểm từ 0 đến 1],
                    "transportation": [Điểm từ 0 đến 1],
                    "tourism": [Điểm từ 0 đến 1],
                    "order": [Điểm từ 0 đến 1],
                    "general": [Điểm từ 0 đến 1]
                }
            }
            
            Tổng của tất cả điểm số nên xấp xỉ bằng 1.0.
            """
            
            # Using OpenAI 0.28.1 format
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                max_tokens=150,   # Limit response size
                n=1,
                stop=None
            )
            
            # Extract the response
            result = response.choices[0].message.content.strip()
            logging.debug(f"Context detection result: {result}")
            
            # Parse the JSON response
            import json
            import re
            
            # Clean up the response if it contains markdown code blocks
            # Pattern to match markdown code blocks: ```json ... ```
            json_pattern = re.compile(r'```(?:json)?\s*(.+?)\s*```', re.DOTALL)
            match = json_pattern.search(result)
            
            if match:
                # Extract the JSON content from the code block
                json_content = match.group(1).strip()
                logging.debug(f"Extracted JSON from markdown: {json_content}")
                context_data = json.loads(json_content)
            else:
                # Try parsing the raw response if no code block is found
                context_data = json.loads(result)
            
            return context_data
            
        except Exception as e:
            logging.error(f"Error detecting context: {e}")
            # Return a default response if there's an error
            return {
                "primary_context": "general",
                "confidence": 1.0,
                "all_contexts": {
                    "restaurant": 0.0,
                    "accommodation": 0.0,
                    "delivery": 0.0,
                    "transportation": 0.0,
                    "tourism": 0.0,
                    "order": 0.0,
                    "general": 1.0
                },
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Initialize the detector
    detector = ContextDetector()
    
    # Test queries
    test_queries = [
        "I'm looking for a good restaurant near me",
        "Do you have any hotel recommendations?",
        "I need a driver to take me to the airport",
        "What are some interesting places to visit?",
        "What's the weather like today?",
        "Kiểm tra lịch sử đơn hàng của tôi",
        "Tôi đã từng đặt dịch vụ nào chưa?"
    ]
    
    # Test the detector
    for query in test_queries:
        result = detector.detect_context(query)
        print(f"Query: {query}")
        print(f"Primary Context: {result['primary_context']} (Confidence: {result['confidence']:.2f})")
        print("All Contexts:")
        for context, score in result['all_contexts'].items():
            print(f"  - {context}: {score:.2f}")
        print()
