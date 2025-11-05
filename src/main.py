import os
import sys

# Add the 'src' directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_gemini import main as gemini_main

def main():
    """
    This is the main entry point for the chatbot application.
    """
    print("Starting the Lendfoundry Chatbot...")
    # You can add logic here to choose between different models (e.g., Gemini, Bedrock)
    # For now, we will directly call the Gemini main function.
    gemini_main()

if __name__ == "__main__":
    main()