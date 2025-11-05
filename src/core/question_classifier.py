import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class QuestionClassifier:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.base_system_prompt = """
[LendFoundry Question Classification] You are an expert at classifying user questions. Your task is to determine if a question is a database query or a general conversational question.

- **Database Query**: A question that is asking for specific information that would be found in a database. Examples: "What is the total number of loans?", "How many active users are there?", "Show me the recent transactions."
- **General Question**: A conversational question or a statement that is not asking for specific data. Examples: "Hello", "How are you?", "What can you do?", "Thank you."

Respond with only "database" or "general".
"""
    
    def classify_question(self, user_question, chat_history=""):
        """
        Classify the user's question as 'database' or 'general'.
        """
        try:
            prompt = f"""{self.base_system_prompt}

Chat History:
{chat_history}

User Question: {user_question}

Classification:
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=256
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
            )
            
            if not response.candidates or response.candidates[0].finish_reason == 2:
                logging.warning("Model returned an empty response for classification or hit the token limit.")
                return "general"

            if response.text:
                return response.text.strip().lower()
            else:
                logging.warning("Model returned an empty response for classification.")
                return "general"
            
        except Exception as e:
            logging.error(f"Error classifying question: {e}")
            return "general" # Default to general if there's an error
