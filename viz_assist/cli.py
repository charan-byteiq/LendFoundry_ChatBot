import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import google.generativeai as genai
import asyncio
import json

# Adjust imports to be relative to the 'src' directory
from agents.langgraph_agent import SQLLangGraphAgentGemini
from db.vector_db_store import store_in_vector_db, get_vector_store
from db.query_runner import RedshiftSQLTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Import schema and document information
from db.table_descriptions_semantic import documents, join_details, schema_info

# Load environment variables from .env file
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


class Chatbot:
    def __init__(self):
        
        # Initialize agent components once for efficiency
        self.vector_store = None
        self.query_runner = None
        self.gemini_agent = None
        self._init_agent_components()
    
    def _init_agent_components(self):
        """Initialize agent components once during chatbot creation"""
        print("Initializing Gemini SQL Agent components...")
        
        # Load existing vector store
        try:
            self.vector_store = get_vector_store()
            if self.vector_store:
                print("✓ Existing vector store loaded successfully.")
            else:
                print("⚠ Warning: No existing vector store found.")
        except Exception as e:
            print(f"✗ Error loading existing vector store: {e}")
            self.vector_store = None
        
        # Initialize Query Runner
        try:
            self.query_runner = RedshiftSQLTool()
            print("✓ Redshift query runner initialized.")
        except Exception as e:
            print(f"⚠ Could not initialize Redshift query runner: {e}")
            self.query_runner = None
        
        # Initialize the Gemini Agent
        if self.vector_store:
            try:
                self.gemini_agent = SQLLangGraphAgentGemini(
                    vector_store=self.vector_store,
                    join_details=join_details,
                    schema_info=schema_info,
                    query_runner=self.query_runner
                )
                print("✓ Gemini SQL LangGraph Agent initialized successfully.\n")
            except Exception as e:
                print(f"✗ Error initializing Gemini agent: {e}")
                self.gemini_agent = None
        else:
            print("✗ Cannot initialize agent without vector store.")
            self.gemini_agent = None

    async def get_existing_vector_store(self):
        """
        Load the existing vector store collection without creating embeddings or re-embedding documents.
        Returns None if the collection does not exist.
        """
        if self.vector_store:
            return self.vector_store
        
        try:
            vector_store = get_vector_store()
            if vector_store:
                print("Existing vector store loaded successfully.")
                self.vector_store = vector_store
            else:
                print("No existing vector store found.")
            return vector_store
        except Exception as e:
            print(f"Error loading existing vector store: {e}")
            return None

    async def get_response(self, user_question: str, thread_id: str = "default"):
        """
        Processes the user's question as a database query with chart analysis.
        
        Args:
            user_question: The user's question
            thread_id: Unique identifier for the conversation thread
        
        Returns:
            dict: Contains SQL query, JSON data, and chart analysis
        """
        print(f"\n{'='*60}")
        print(f"Processing query for thread: {thread_id}")
        print(f"{'='*60}")
        
        # Check if agent is initialized
        if not self.gemini_agent:
            return {"error": "SQL Agent not initialized. Please check if vector store exists."}
        
        if not self.vector_store:
            return {"error": "No existing vector store found. Please create the vector store first."}

        print(f"\n📝 User Question: '{user_question}'")

        try:
            # Process the user question with thread_id
            result = self.gemini_agent.process_query(user_question, thread_id=thread_id)

            # Display results
            self._display_results(result)
            
            return result

        except Exception as e:
            print(f"\n✗ Error occurred during query processing: {e}")
            return {"error": f"An error occurred during query processing: {e}"}
    
    def _display_results(self, result: dict):
        """Display formatted results with chart analysis"""
        print(f"\n{'='*60}")
        print("QUERY RESULTS")
        print(f"{'='*60}")
        
        if not result.get('success'):
            print(f"\n✗ Error: {result.get('error')}")
            return
        
        # Display SQL Query
        print(f"\n📊 SQL Query Generated:")
        print("-" * 60)
        print(result.get('cleaned_sql_query', 'N/A'))
        print("-" * 60)
        
        # Display JSON Data
        print(f"\n📦 Data (JSON Format):")
        print("-" * 60)
        json_data = result.get('execution_data_json', '{}')
        try:
            # Pretty print JSON
            parsed_json = json.loads(json_data)
            print(json.dumps(parsed_json, indent=2))
            
            # Show record count
            if isinstance(parsed_json, list):
                print(f"\n📈 Total Records: {len(parsed_json)}")
        except json.JSONDecodeError:
            print(json_data)
        print("-" * 60)
        
        # Display Chart Analysis
        chart_analysis = result.get('chart_analysis', {})
        if chart_analysis:
            print(f"\n📊 Chart Analysis:")
            print("-" * 60)
            print(f"Chartable: {'✓ Yes' if chart_analysis.get('chartable') else '✗ No'}")
            print(f"Reasoning: {chart_analysis.get('reasoning', 'N/A')}")
            
            if chart_analysis.get('chartable'):
                # Display recommended chart
                auto_chart = chart_analysis.get('auto_chart', {})
                print(f"\n🎯 Recommended Chart:")
                print(f"  Type: {auto_chart.get('type', 'N/A')}")
                print(f"  Title: {auto_chart.get('title', 'N/A')}")
                print(f"  X-axis: {auto_chart.get('x_axis', 'N/A')}")
                print(f"  Y-axis: {auto_chart.get('y_axis', 'N/A')}")
                print(f"  Reason: {auto_chart.get('reason', 'N/A')}")
                
                # Display alternative suggestions
                suggested_charts = chart_analysis.get('suggested_charts', [])
                if suggested_charts:
                    print(f"\n💡 Alternative Chart Options:")
                    for idx, chart in enumerate(suggested_charts, 1):
                        print(f"  {idx}. {chart.get('type', 'N/A')} - {chart.get('title', 'N/A')}")
                        print(f"     Confidence: {chart.get('confidence', 'N/A')}")
            print("-" * 60)
        
        print(f"\n{'='*60}\n")
    
    def reinitialize_agent(self):
        """Reinitialize the agent (useful if vector store is updated)"""
        print("Reinitializing agent components...")
        self._init_agent_components()
    
    def get_agent_status(self):
        """Get the initialization status of agent components"""
        return {
            "vector_store_loaded": self.vector_store is not None,
            "query_runner_loaded": self.query_runner is not None,
            "agent_initialized": self.gemini_agent is not None
        }


# Main function
async def main():
    """Main function to run the chatbot"""
    print("\n" + "="*60)
    print("SQL CHATBOT WITH VISUALIZATION ANALYSIS")
    print("="*60 + "\n")
    
    # Initialize chatbot
    chatbot = Chatbot()
    
    # Check agent status
    status = chatbot.get_agent_status()
    if not status['agent_initialized']:
        print("✗ Failed to initialize chatbot. Exiting...")
        return
    
    # Demo mode: Single query
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_questions = [
            "How many loans were onboarded in the last 3 months?",
            "Show me the top 10 borrowers by total loan amount",
            "What is the distribution of loans by status?"
        ]
        
        print("Running in DEMO mode with sample questions...\n")
        for idx, question in enumerate(demo_questions, 1):
            print(f"\n{'#'*60}")
            print(f"DEMO QUERY {idx}/{len(demo_questions)}")
            print(f"{'#'*60}")
            await chatbot.get_response(question, thread_id=f"demo_thread_{idx}")
            
            if idx < len(demo_questions):
                await asyncio.sleep(2)  # Pause between queries
        
        print("\n✓ Demo completed!")
        return
    
    # Interactive mode
    print("Starting in INTERACTIVE mode...")
    print("Commands:")
    print("  - Type your question to query the database")
    print("  - Type 'status' to check agent status")
    print("  - Type 'exit' or 'quit' to end the session")
    print("  - Type 'new' to start a new conversation thread\n")
    
    thread_id = "default"
    conversation_count = 0
    
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye! Thank you for using the SQL Chatbot.")
                break
            
            elif user_input.lower() == 'status':
                status = chatbot.get_agent_status()
                print("\n📊 Agent Status:")
                print(f"  Vector Store: {'✓ Loaded' if status['vector_store_loaded'] else '✗ Not Loaded'}")
                print(f"  Query Runner: {'✓ Loaded' if status['query_runner_loaded'] else '✗ Not Loaded'}")
                print(f"  Agent: {'✓ Initialized' if status['agent_initialized'] else '✗ Not Initialized'}")
                continue
            
            elif user_input.lower() == 'new':
                conversation_count += 1
                thread_id = f"thread_{conversation_count}"
                print(f"\n🔄 Started new conversation thread: {thread_id}")
                continue
            
            # Process query
            result = await chatbot.get_response(user_input, thread_id=thread_id)
            
            # Optionally save results to file
            if result.get('success') and result.get('chart_analysis', {}).get('chartable'):
                save_option = input("\n💾 Save results to file? (y/n): ").strip().lower()
                if save_option == 'y':
                    filename = f"query_result_{thread_id}_{asyncio.get_event_loop().time():.0f}.json"
                    with open(filename, 'w') as f:
                        json.dump({
                            'question': user_input,
                            'sql_query': result.get('cleaned_sql_query'),
                            'data': json.loads(result.get('execution_data_json', '{}')),
                            'chart_analysis': result.get('chart_analysis')
                        }, f, indent=2)
                    print(f"✓ Results saved to: {filename}")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            continue


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
