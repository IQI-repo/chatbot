import os
import json
import logging
import ijson
from typing import List, Dict, Union, Generator, Optional, Tuple

class DocumentLoader:
    def __init__(self, documents_path: str):
        self.documents_path = documents_path
        self._cached_data = None
        self._cached_filename = None

    def load_documents(self) -> List[str]:
        documents = []
        for filename in os.listdir(self.documents_path):
            if filename.endswith('.txt'):
                with open(os.path.join(self.documents_path, filename), 'r') as file:
                    documents.append(file.read())
        return documents
    
    def load_json_data(self, filename: str = 'data_fixed.json', use_streaming: bool = True, 
                      start_index: int = 0, limit: Optional[int] = None) -> List[Dict]:
        """Load and parse JSON data from a file with pagination support.
        
        Args:
            filename: Name of the JSON file to load
            use_streaming: Whether to use streaming parser for large files
            start_index: Starting index for pagination
            limit: Maximum number of items to return (None for all)
            
        Returns:
            List of dictionaries containing the JSON data
        """
        logging.info(f"Attempting to load JSON data from file: {filename} (streaming={use_streaming})")
        file_path = os.path.join(self.documents_path, filename)
        logging.debug(f"Full file path: {file_path}")
        
        # Check if we can use cached data
        if self._cached_data is not None and self._cached_filename == filename and not use_streaming:
            logging.info(f"Using cached data for {filename}")
            if limit is not None:
                return self._cached_data[start_index:start_index + limit]
            else:
                return self._cached_data[start_index:]
        
        if not os.path.exists(file_path):
            self._log_missing_file(file_path)
            return []
            
        logging.info(f"File exists: {file_path}")
        
        try:
            if use_streaming:
                return self._load_json_streaming(file_path, start_index, limit)
            else:
                return self._load_json_full(file_path, start_index, limit)
        except Exception as e:
            logging.error(f"Error loading JSON file: {e}")
            return []
    
    def _load_json_full(self, file_path: str, start_index: int = 0, 
                       limit: Optional[int] = None) -> List[Dict]:
        """Load the entire JSON file into memory at once."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logging.info(f"Successfully loaded JSON data with {len(data)} items")
                
                # Cache the data for future use
                self._cached_data = data
                self._cached_filename = os.path.basename(file_path)
                
                # Apply pagination
                if limit is not None:
                    return data[start_index:start_index + limit]
                else:
                    return data[start_index:]
                    
        except json.JSONDecodeError as e:
            self._handle_json_decode_error(file_path, e)
            return []
    
    def _load_json_streaming(self, file_path: str, start_index: int = 0, 
                            limit: Optional[int] = None) -> List[Dict]:
        """Load JSON data using streaming parser to handle large files efficiently."""
        try:
            result = []
            count = 0
            end_index = float('inf') if limit is None else start_index + limit
            
            with open(file_path, 'rb') as file:
                # Assuming the JSON file contains an array of objects
                for item in ijson.items(file, 'item'):
                    if count >= start_index and count < end_index:
                        result.append(item)
                    count += 1
                    if count >= end_index:
                        break
            
            logging.info(f"Successfully loaded {len(result)} items using streaming parser")
            return result
            
        except Exception as e:
            logging.error(f"Error in streaming JSON parser: {e}")
            # Fall back to non-streaming method if streaming fails
            logging.info("Falling back to non-streaming JSON loading")
            return self._load_json_full(file_path, start_index, limit)
    
    def get_json_data_count(self, filename: str = 'data_fixed.json') -> int:
        """Get the total count of items in a JSON file without loading all data."""
        file_path = os.path.join(self.documents_path, filename)
        
        if not os.path.exists(file_path):
            self._log_missing_file(file_path)
            return 0
            
        try:
            # Try to use cached data if available
            if self._cached_data is not None and self._cached_filename == filename:
                return len(self._cached_data)
                
            # Otherwise count items using streaming parser
            count = 0
            with open(file_path, 'rb') as file:
                for _ in ijson.items(file, 'item'):
                    count += 1
            return count
        except Exception as e:
            logging.error(f"Error counting JSON items: {e}")
            return 0
    
    def stream_json_data(self, filename: str = 'data_fixed.json', 
                        batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Stream JSON data in batches to avoid loading everything at once.
        
        Args:
            filename: Name of the JSON file to stream
            batch_size: Number of items to yield in each batch
            
        Yields:
            Batches of JSON data items
        """
        file_path = os.path.join(self.documents_path, filename)
        
        if not os.path.exists(file_path):
            self._log_missing_file(file_path)
            return
            
        try:
            batch = []
            with open(file_path, 'rb') as file:
                for item in ijson.items(file, 'item'):
                    batch.append(item)
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                        
            # Yield any remaining items
            if batch:
                yield batch
                
        except Exception as e:
            logging.error(f"Error streaming JSON data: {e}")
            yield []
    
    def _handle_json_decode_error(self, file_path: str, error: json.JSONDecodeError) -> None:
        """Handle JSON decode errors with detailed logging."""
        logging.error(f"JSON decode error: {error}")
        logging.error(f"Error occurred at line {error.lineno}, column {error.colno}")
        
        # Try to read the problematic line
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if error.lineno <= len(lines):
                    logging.error(f"Problematic line: {lines[error.lineno-1].strip()}")
        except Exception as read_err:
            logging.error(f"Could not read problematic line: {read_err}")
    
    def _log_missing_file(self, file_path: str) -> None:
        """Log information about missing files."""
        logging.error(f"File does not exist: {file_path}")
        # List available files in the directory
        try:
            dir_path = os.path.dirname(file_path)
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                logging.info(f"Available files in {dir_path}: {files}")
        except Exception as e:
            logging.error(f"Error listing directory: {e}")