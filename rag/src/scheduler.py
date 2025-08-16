import logging
import importlib
import inspect
import os
import sys
import time
from typing import Dict, List, Any, Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class RagScheduler:
    """
    Class for scheduling periodic refresh of Qdrant data from _rag.py files
    """
    
    def __init__(self, refresh_interval_minutes: int = 10):
        """
        Initialize the RagScheduler
        
        Args:
            refresh_interval_minutes: Interval in minutes to refresh data
        """
        self.refresh_interval = refresh_interval_minutes
        self.scheduler = BackgroundScheduler()
        self.rag_modules = {}
        self.rag_functions = {}
        logging.info(f"RagScheduler initialized with refresh interval of {refresh_interval_minutes} minutes")
    
    def discover_rag_modules(self, src_dir: str = "src"):
        """
        Discover all _rag.py modules in the src directory
        
        Args:
            src_dir: Directory to search for _rag.py files
        """
        try:
            # Add src directory to path if not already there
            src_path = os.path.abspath(src_dir)
            if src_path not in sys.path:
                sys.path.append(src_path)
            
            # Find all _rag.py files
            rag_files = []
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    if file.endswith("_rag.py"):
                        rel_path = os.path.relpath(os.path.join(root, file), src_path)
                        module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, ".")
                        rag_files.append(module_name)
            
            # Import modules
            for module_name in rag_files:
                try:
                    module = importlib.import_module(module_name)
                    self.rag_modules[module_name] = module
                    logging.info(f"Discovered RAG module: {module_name}")
                except ImportError as e:
                    logging.error(f"Error importing module {module_name}: {str(e)}")
            
            logging.info(f"Discovered {len(self.rag_modules)} RAG modules")
            
        except Exception as e:
            logging.error(f"Error discovering RAG modules: {str(e)}")
    
    def discover_refresh_functions(self):
        """
        Discover refresh functions in the RAG modules
        """
        for module_name, module in self.rag_modules.items():
            # Look for classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith("RAG"):
                    # Look for refresh methods in the class
                    for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                        if "refresh" in method_name.lower() or "update" in method_name.lower() or "load" in method_name.lower():
                            self.rag_functions[f"{module_name}.{name}.{method_name}"] = {
                                "class": obj,
                                "method": method_name
                            }
                            logging.info(f"Discovered refresh function: {module_name}.{name}.{method_name}")
        
        logging.info(f"Discovered {len(self.rag_functions)} refresh functions")
    
    def refresh_all_data(self):
        """
        Refresh all data by calling all discovered refresh functions
        """
        logging.info("Starting data refresh...")
        
        for func_name, func_info in self.rag_functions.items():
            try:
                # Create an instance of the class
                instance = func_info["class"]()
                
                # Get the method
                method = getattr(instance, func_info["method"])
                
                # Call the method
                logging.info(f"Calling {func_name}...")
                method()
                logging.info(f"Successfully refreshed data with {func_name}")
                
            except Exception as e:
                logging.error(f"Error refreshing data with {func_name}: {str(e)}")
        
        logging.info("Data refresh completed")
    
    def start(self):
        """
        Start the scheduler
        """
        try:
            # Discover RAG modules and refresh functions
            self.discover_rag_modules()
            self.discover_refresh_functions()
            
            if not self.rag_functions:
                logging.warning("No refresh functions discovered, scheduler will not be started")
                return
            
            # Add job to refresh data periodically
            self.scheduler.add_job(
                self.refresh_all_data,
                IntervalTrigger(minutes=self.refresh_interval),
                id="refresh_data",
                name="Refresh RAG Data",
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            logging.info(f"Scheduler started, will refresh data every {self.refresh_interval} minutes")
            
            # Run initial refresh
            self.refresh_all_data()
            
        except Exception as e:
            logging.error(f"Error starting scheduler: {str(e)}")
    
    def stop(self):
        """
        Stop the scheduler
        """
        try:
            self.scheduler.shutdown()
            logging.info("Scheduler stopped")
        except Exception as e:
            logging.error(f"Error stopping scheduler: {str(e)}")

# Example usage
if __name__ == "__main__":
    scheduler = RagScheduler(refresh_interval_minutes=10)
    scheduler.start()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
