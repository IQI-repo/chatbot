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
            You are a context detection system. Your task is to analyze the user's query and determine 
            which service category they are referring to. Respond with a JSON object only, no explanations.
            
            Available service categories:
            - restaurant: Anything related to food, dining, restaurants, cafes, meals, etc.
            - accommodation: Anything related to hotels, resorts, homestays, rooms, lodging, etc.
            - transportation: Anything related to drivers, taxis, car services, transportation, etc.
            - tourism: Anything related to tours, attractions, sightseeing, activities, etc.
            - general: General queries not specific to any service
            
            Your response should be in this format:
            {
                "primary_context": "category_name",
                "confidence": 0.XX,
                "all_contexts": {
                    "restaurant": 0.XX,
                    "accommodation": 0.XX,
                    "transportation": 0.XX,
                    "tourism": 0.XX,
                    "general": 0.XX
                }
            }
            
            The confidence scores should sum to 1.0 across all categories.
            """
            
            # Using OpenAI 0.28.1 format
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
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
                    "transportation": 0.0,
                    "tourism": 0.0,
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
        "What's the weather like today?"
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
