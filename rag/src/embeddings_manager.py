from typing import List
import openai
import numpy as np
import logging

class EmbeddingsManager:
    def __init__(self, api_key: str):
        # Initialize OpenAI with API key
        try:
            # For OpenAI 0.28.1, we just set the API key
            openai.api_key = api_key
            logging.info("OpenAI API key set successfully")
        except Exception as e:
            logging.error(f"Error setting OpenAI API key: {e}")
            raise

    def create_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        embeddings = []
        try:
            logging.debug(f"Creating embeddings for {len(texts)} texts")
            for i, text in enumerate(texts):
                try:
                    # For OpenAI 0.28.1, the response format is different
                    response = openai.Embedding.create(
                        model="text-embedding-ada-002",
                        input=text
                    )
                    # Extract embedding from the response (different format in 0.28.1)
                    embeddings.append(np.array(response['data'][0]['embedding']))
                    if i % 10 == 0 and i > 0:
                        logging.debug(f"Processed {i} embeddings so far")
                except Exception as e:
                    logging.error(f"Error creating embedding for text {i}: {e}")
                    # Create a zero embedding as fallback
                    embeddings.append(np.zeros(1536))  # Ada embeddings are 1536 dimensions
            logging.info(f"Successfully created {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logging.error(f"Error in create_embeddings: {e}")
            raise