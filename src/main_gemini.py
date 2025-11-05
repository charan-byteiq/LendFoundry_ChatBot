import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from langchain_classic.memory import ConversationBufferMemory
import google.generativeai as genai

# Adjust imports to be relative to the 'src' directory
from src.agents.gemini.sql_langgraph_agent_gemini import SQLLangGraphAgentGemini
from src.db.vector_db_store import store_in_vector_db
from src.db.query_runner import RedshiftSQLTool
from src.core.question_classifier import QuestionClassifier
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Import schema and document information
# Assuming table_updated_desc.py is in the root or accessible in PYTHONPATH
from db.table_descriptions_semantic import documents, join_details, schema_info

# Load environment variables from .env file
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

class Chatbot:
    def __init__(self):
        self.memory = ConversationBufferMemory()
        self.classifier = QuestionClassifier()
        
        # Modern LangChain setup for general responses
        self.general_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            max_tokens=400
        )
        self.general_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized database assistant designed exclusively to help users with database queries, data analysis, and data-related tasks.
                                ## STRICT OPERATIONAL BOUNDARIES

                                **DO NOT answer questions about:**
                                - General knowledge (geography, history, science, etc.)
                                - Current events or news
                                - Personal advice or opinions
                                - Technical topics unrelated to databases
                                - Entertainment, sports, or lifestyle topics
                                - Math problems unrelated to data analysis
                                - Any topic that is not directly related to database operations or data management

                                **ALWAYS REFUSE these types of questions politely and redirect to your core function.**

                                ## Your ONLY Responsibilities:
                                - Help with understanding the database 
                                - Assist with details from the database 
                                - Generating SQL queries related to the database
                                - Analyzing data from the database


                                ## Response Strategy for Out-of-Scope Questions:

                                **For general knowledge questions** (like "What is the capital of France?"):
                                "I'm a specialized database assistant and can only help with database queries and data analysis. What database-related task can I assist you with today?"

                                **For unrelated technical questions:**
                                "I focus specifically on database and data analysis tasks. Is there any data you need to query or analyze?"

                                **For personal/lifestyle questions:**
                                "I'm designed to help with database operations only. Do you have any data queries I can help you with?"

                                ## Acceptable General Interactions:
                                - Brief greetings: Respond warmly but immediately mention your database focus
                                - Thank you messages: Acknowledge politely and ask about database needs
                                - Clarification requests about database topics: Always helpful

                                ## Core Personality:
                                - Professional and helpful for database tasks
                                - Polite but firm about staying within scope
                                - Always redirect to database capabilities
                                - Never apologize excessively for declining - be confident in your role

                                Remember: Your value comes from being an expert database assistant, not a general knowledge chatbot. Stay focused on your core mission.
"""),
            ("human", "{question}")
        ])
        self.general_chain = self.general_prompt | self.general_llm

    async def get_response(self, user_question):
        """
        Classifies the user's question and responds accordingly.
        """
        # Classify the question
        chat_history = self.memory.load_memory_variables({})
        classification = self.classifier.classify_question(user_question, chat_history)
        print(f"Question classified as: {classification}")

        if "database" in classification:
            return await self.get_database_response(user_question)
        else:
            return await self.get_general_response(user_question)

    async def get_general_response(self, user_question):
        """
        Generates a general conversational response using an LCEL chain.
        """
        try:
            response_message = await self.general_chain.ainvoke({"question": user_question})
            response_text = response_message.content
            self.memory.save_context({"input": user_question}, {"output": response_text})
            return {"success": True, "execution_result": response_text}
        except Exception as e:
            print(f"Error generating general response: {e}")
            return {"error": f"Error generating general response: {e}"}

    async def get_database_response(self, user_question):
        """
        Initializes and runs the Gemini SQL LangGraph agent for a given user question.
        """
        print("Initializing Gemini SQL Agent...")

        # 1. Initialize Embeddings
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
            print("Embeddings initialized successfully.")
        except Exception as e:
            print(f"Error initializing embeddings: {e}")
            return {"error": f"Error initializing embeddings: {e}"}

        # 2. Prepare documents and Vector Store
        try:
            # Flatten the list of documents if it's nested
            flat_splits = [d for doc_list in documents for d in (doc_list if isinstance(doc_list, list) else [doc_list])]
            
            # Create or load the vector store. 
            # Set force_recreate=True to delete the old vector store and create a new one.
            vector_store = store_in_vector_db(flat_splits, embeddings, force_recreate=False)
            print("Vector store created successfully.")
        except Exception as e:
            print(f"Error creating vector store: {e}")
            return {"error": f"Error creating vector store: {e}"}

        # 3. Initialize Query Runner (optional)
        try:
            query_runner = RedshiftSQLTool()
            print("Redshift query runner initialized.")
        except Exception as e:
            print(f"Could not initialize Redshift query runner: {e}")
            query_runner = None

        # 4. Initialize the Gemini Agent
        try:
            gemini_agent = SQLLangGraphAgentGemini(
                vector_store=vector_store,
                embeddings=embeddings,
                join_details=join_details,
                schema_info=schema_info,
                query_runner=query_runner,
                memory=self.memory
            )
            print("Gemini SQL LangGraph Agent initialized successfully.")
        except Exception as e:
            print(f"Error initializing Gemini agent: {e}")
            return {"error": f"Error initializing Gemini agent: {e}"}

        # 5. Process the user question
        print(f"\nProcessing user question: '{user_question}'")
        
        try:
            result = gemini_agent.process_query(user_question)
            
            # Print the final result
            print("\n--- Agent Final Result ---")
            print(f"Success: {result.get('success')}")
            if result.get('success'):
                print(f"User Question: {result.get('user_question')}")
                print(f"Cleaned SQL Query: {result.get('cleaned_sql_query')}")
                print(f"Execution Result: {result.get('execution_result', 'N/A')}")
            else:
                print(f"Error: {result.get('error')}")
            print("--------------------------")
            return result

        except Exception as e:
            print(f"An error occurred during query processing: {e}")
            return {"error": f"An error occurred during query processing: {e}"}

async def main():
    """
    Main function to run the Gemini SQL LangGraph agent with a simulated conversation.
    """
    print("Chatbot initialized for a simulated conversation.")
    
    # Initialize chatbot
    chatbot = Chatbot()

    # --- First Question (Database) ---
    user_question_1 = "What is the total number of loans?"
    print(f"You: {user_question_1}")
    
    result_1 = await chatbot.get_response(user_question_1)
    
    print("\n--- Chatbot Response ---")
    if result_1 and result_1.get('success'):
        answer_1 = result_1.get('execution_result', 'No execution result found.')
        print(f"Bot: {answer_1}")
    elif result_1:
        error_message_1 = result_1.get('error', 'An unknown error occurred.')
        print(f"Bot: I'm sorry, I encountered an error: {error_message_1}")
    else:
        print("Bot: I'm sorry, something went wrong and I didn't get a result.")
    print("------------------------\n")

    # --- Second Question (General) ---
    user_question_2 = "Hello, how are you?"
    print(f"You: {user_question_2}")

    result_2 = await chatbot.get_response(user_question_2)

    print("\n--- Chatbot Response ---")
    if result_2 and result_2.get('success'):
        answer_2 = result_2.get('execution_result', 'No execution result found.')
        print(f"Bot: {answer_2}")
    elif result_2:
        error_message_2 = result_2.get('error', 'An unknown error occurred.')
        print(f"Bot: I'm sorry, I encountered an error: {error_message_2}")
    else:
        print("Bot: I'm sorry, something went wrong and I didn't get a result.")
    print("------------------------\n")

    # --- Third Question (Database Follow-up) ---
    user_question_3 = "How many of them are active?"
    print(f"You: {user_question_3}")

    result_3 = await chatbot.get_response(user_question_3)

    print("\n--- Chatbot Response ---")
    if result_3 and result_3.get('success'):
        answer_3 = result_3.get('execution_result', 'No execution result found.')
        print(f"Bot: {answer_3}")
    elif result_3:
        error_message_3 = result_3.get('error', 'An unknown error occurred.')
        print(f"Bot: I'm sorry, I encountered an error: {error_message_3}")
    else:
        print("Bot: I'm sorry, something went wrong and I didn't get a result.")
    print("------------------------\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
