import os
import logging
import json
from typing import Dict, List, Any, Optional
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class WebSearch:
    """
    Class for performing web searches using OpenAI API
    """
    
    def __init__(self):
        """
        Initialize the WebSearch class with OpenAI API key
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logging.warning("OPENAI_API_KEY not found in environment variables")
        else:
            openai.api_key = self.api_key
            logging.info("WebSearch initialized with OpenAI API key")
    
    def search_web(self, query: str) -> Dict[str, Any]:
        """
        Search the web for information related to the query
        
        Args:
            query: The user's question
            
        Returns:
            Dictionary containing search results and formatted answer
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "answer": "Không thể tìm kiếm trên internet do thiếu API key.",
                    "search_results": []
                }
            
            logging.info(f"Performing web search for: {query}")
            
            # Use OpenAI's API to perform a web search
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý tìm kiếm thông tin trên internet. Hãy tìm kiếm thông tin liên quan đến câu hỏi của người dùng và trả về kết quả chính xác nhất. Trả lời bằng tiếng Việt."},
                    {"role": "user", "content": f"Tìm kiếm thông tin về: {query}"}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract the search results from the OpenAI response
            search_result = response.choices[0].message.content
            
            # Format the answer in the style of Bé Bơ
            formatted_answer = self._format_answer_as_be_bo(search_result)
            
            return {
                "success": True,
                "answer": formatted_answer,
                "search_results": [search_result]
            }
            
        except Exception as e:
            logging.error(f"Error during web search: {str(e)}")
            return {
                "success": False,
                "answer": f"Em xin lỗi, em không thể tìm kiếm thông tin lúc này. Lỗi: {str(e)}",
                "search_results": []
            }
    
    def _format_answer_as_be_bo(self, search_result: str) -> str:
        """
        Format the search result in the style of Bé Bơ
        
        Args:
            search_result: The raw search result from OpenAI
            
        Returns:
            Formatted answer in the style of Bé Bơ
        """
        try:
            # Use OpenAI to reformat the answer in Bé Bơ's style
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """
                    Bạn là Bé Bơ, một trợ lý thông minh và thân thiện của dịch vụ ShipperRachGia.vn.
                    
                    Hướng dẫn cách trả lời:
                    1. QUAN TRỌNG NHẤT: Luôn trả lời hoàn toàn bằng tiếng Việt, không bao giờ sử dụng tiếng Anh hoặc bất kỳ ngôn ngữ nào khác, dù chỉ là một từ.
                    2. Giới thiệu bản thân là "Em là Bé Bơ" khi bắt đầu cuộc trò chuyện.
                    3. Sử dụng ngôn ngữ tích cực, nhiệt tình và thể hiện sự quan tâm đến người dùng.
                    4. Khi trả lời về nhà hàng, khách sạn hoặc dịch vụ, hãy dựa vào thông tin được cung cấp trong ngữ cảnh.
                    5. Nếu không có thông tin trong ngữ cảnh, hãy hướng dẫn người dùng truy cập website https://shipperrachgia.vn/ để biết thêm chi tiết.
                    6. Tránh sử dụng từ ngữ phức tạp hoặc thuật ngữ chuyên ngành khi không cần thiết.
                    7. Khi đề cập đến giá cả, hãy luôn sử dụng đơn vị tiền tệ VND.
                    8. Nếu người dùng hỏi về thông tin cá nhân hoặc dữ liệu nhạy cảm, lịch sự từ chối và đề xuất họ liên hệ trực tiếp với dịch vụ khách hàng.
                    9. Khi không chắc chắn về thông tin, hãy thừa nhận điều đó thay vì đưa ra thông tin không chính xác.
                    10. Kết thúc câu trả lời với cụm từ thân thiện như "Bé Bơ rất vui được hỗ trợ bạn!" hoặc "Bạn cần Bé Bơ hỗ trợ gì thêm không?".
                    11. Ngay cả khi người dùng hỏi bằng tiếng Anh, vẫn phải trả lời bằng tiếng Việt.
                    """},
                    {"role": "user", "content": f"Đây là thông tin tìm được trên internet: {search_result}\n\nHãy trả lời với phong cách của Bé Bơ, thân thiện và dễ thương."}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            formatted_answer = response.choices[0].message.content
            return formatted_answer
            
        except Exception as e:
            logging.error(f"Error formatting answer: {str(e)}")
            return f"Xin chào anh! Em là Bé Bơ đây ạ! ❤️\n\nEm tìm được thông tin sau trên internet: {search_result}\n\nEm là Bé Bơ luôn sẵn sàng phục vụ anh! 🥰"
