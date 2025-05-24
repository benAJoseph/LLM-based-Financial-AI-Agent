import os
from typing import Dict, Any
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

class FinancialLLMAgent:
    """
    A simplified class to handle financial data analysis using Google's Gemini API.
    """
    
    def __init__(self):
        """Initialize the Financial AI Agent with Gemini API."""
        self.client = None
        self.model_name = "gemini-2.0-flash"
        self._initialize_gemini()
    
    def _initialize_gemini(self) -> None:
        """Initialize the Gemini API client."""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            self.client = genai.Client(api_key=api_key)
            print(f"✅ Financial AI Agent initialized with {self.model_name}")
            
        except Exception as e:
            error_msg = f"❌ Failed to initialize Gemini API: {e}"
            print(error_msg)
            raise RuntimeError(error_msg) from e
    
    def query_financial_data(self, prompt: str, context: str = "") -> Dict[str, Any]:
        """
        Query the Gemini model with a financial prompt and optional context.
        
        Args:
            prompt: The user's query about financial data
            context: Optional context or additional information to include in the query
            
        Returns:
            dict: The model's response and metadata
        """
        try:
            # Prepare the content with context if provided
            content = f"{context}\n\nQuestion: {prompt}"
            
            # Generate content using the client
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=content
            )
            
            return {
                'success': True,
                'response': response.text,
                'model': self.model_name
            }
            
        except Exception as e:
            error_msg = f"Error querying Gemini: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'response': None
            }
    