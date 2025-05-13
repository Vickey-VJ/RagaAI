import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
import requests # Added for calling RetrieverService
import json     # Added for handling JSON payloads

# Determine the project root path (one level up from the 'agents' directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Load environment variables from .env file
if os.path.exists(DOTENV_PATH):
    print(f"Loading .env file from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH, override=True) 
else:
    print(f".env file not found at: {DOTENV_PATH}. Relying on shell environment variables.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "gemini-1.5-flash-latest") 

DEFAULT_FINANCIAL_SYSTEM_PROMPT = """You are a specialized financial assistant. Your goal is to provide concise, accurate, and actionable insights based on the provided context. Focus on market analysis, risk assessment, and identifying key financial events like earnings surprises. Avoid speculation and stick to the data."""

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

# Configuration for the Retriever Service
RETRIEVER_SERVICE_BASE_URL = os.getenv("RETRIEVER_SERVICE_URL", "http://localhost:8002/retriever")

class LanguageAgent:
    def __init__(self, model_name: str = LLM_MODEL_NAME):
        print(f"Initializing LanguageAgent with model: {model_name}")
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=GEMINI_API_KEY,
            )
            print("ChatGoogleGenerativeAI model initialized successfully.")
        except Exception as e:
            print(f"Error initializing ChatGoogleGenerativeAI: {e}")
            raise

    def _fetch_context_from_retriever(self, query: str, top_k: int = 3) -> list[str]:
        """
        Fetches relevant context documents from the RetrieverService.
        """
        try:
            search_url = f"{RETRIEVER_SERVICE_BASE_URL}/search"
            payload = {"query": query, "top_k": top_k}
            print(f"Querying RetrieverService at {search_url} with query: '{query}', top_k: {top_k}")
            
            # Ensure the retriever service is running for this to work
            response = requests.post(search_url, json=payload, timeout=10) # Increased timeout
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            
            results = response.json().get("results", [])
            documents = [result.get("text") for result in results if result.get("text")]
            
            print(f"Retrieved {len(documents)} documents from RetrieverService.")
            if documents:
                for i, doc in enumerate(documents):
                    print(f"  Doc {i+1}: {doc[:100]}...") # Log first 100 chars of each doc
            return documents
        except requests.exceptions.Timeout:
            print(f"Timeout error calling RetrieverService at {search_url}. Is the service running and responsive?")
            return []
        except requests.exceptions.ConnectionError:
            print(f"Connection error calling RetrieverService at {search_url}. Is the service running?")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error calling RetrieverService: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from RetrieverService: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching context from retriever: {e}")
            import traceback
            traceback.print_exc()
            return []

    def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generates a response from the LLM given a user prompt and an optional system prompt.
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        
        print(f"Sending prompt to LLM: '{prompt}' (System: '{system_prompt if system_prompt else 'None'}')")
        try:
            response = self.llm.invoke(messages)
            print(f"LLM Response received: {response.content[:100]}...") # Log first 100 chars
            return response.content
        except Exception as e:
            print(f"Error during LLM invocation: {e}")
            return "Sorry, I encountered an error while generating a response."

    def generate_rag_response(self, prompt: str, use_rag: bool = True, top_k_retrieval: int = 3, system_prompt: str = None) -> str:
        """
        Generates a response using the LLM. If use_rag is True, it first fetches context
        from the RetrieverService and incorporates it into the prompt.
        It now uses a more structured approach for financial queries.
        """
        context_str = ""
        if use_rag:
            print(f"RAG mode enabled. Fetching context for prompt: '{prompt}'")
            # For financial queries, the prompt itself might be specific,
            # but the underlying entities (e.g., "Asia tech stocks", "earnings") guide retrieval.
            context_docs = self._fetch_context_from_retriever(query=prompt, top_k=top_k_retrieval)
            
            if context_docs:
                context_str = "\n\nRelevant Information Retrieved from Knowledge Base:\n"
                for i, doc in enumerate(context_docs):
                    context_str += f"{i+1}. {doc}\n"
                print("Context retrieved for RAG.")
            else:
                print("No context documents retrieved for RAG.")

        # Construct the final prompt using the original user query and the retrieved context
        # The system prompt will guide the LLM on how to interpret and use this information.
        
        # Example of a specific financial query structure:
        # "What’s our risk exposure in Asia tech stocks today, and highlight any earnings surprises?"
        # The 'prompt' variable will hold this query.
        
        # The final prompt passed to the LLM will be the user's query,
        # potentially augmented by the context if found.
        # The system prompt (DEFAULT_FINANCIAL_SYSTEM_PROMPT or custom) will frame the task.

        final_user_prompt = prompt
        if context_str:
            final_user_prompt = f"""Based on the following information:
{context_str}

Please answer the question: {prompt}"""
        else:
            final_user_prompt = prompt # Use original prompt if no context

        # Use the default financial system prompt if no specific system_prompt is provided
        current_system_prompt = system_prompt if system_prompt else DEFAULT_FINANCIAL_SYSTEM_PROMPT
        
        print(f"Final prompt for LLM: '{final_user_prompt}'")
        print(f"System prompt for LLM: '{current_system_prompt}'")

        return self.generate_response(prompt=final_user_prompt, system_prompt=current_system_prompt)

if __name__ == '__main__':
    print("--- Initializing LanguageAgent for testing ---")
    # IMPORTANT: For RAG tests to work, the RetrieverService (retriever_service.py)
    # must be running (default: http://localhost:8002) and its vector store populated.
    # The default vector store data is in /data/vector_store/ which includes sample sentences.
    # Ensure RETRIEVER_SERVICE_URL in .env is correct if not using the default.

    try:
        agent = LanguageAgent()
        print("--- LanguageAgent Initialized ---\n")

        # Test 1: Simple prompt (RAG will be attempted but might find no specific context or service might be down)
        print("--- Test 1: Simple Prompt (RAG will be attempted) ---")
        user_prompt_1 = "What is the capital of France?"
        response_1 = agent.generate_rag_response(user_prompt_1) # Uses default financial system prompt now
        print(f"User Prompt 1: {user_prompt_1}")
        print(f"LLM Response 1: {response_1}\n")

        # Test 2: RAG-enabled prompt - query designed to hit sample data in vector store
        # Sample data in text_data.pkl (from your workspace view) includes:
        # - "Apple Inc. reported a significant increase in iPhone sales during the last quarter."
        # - "Microsoft Azure continues to show strong growth in the cloud computing market."
        # - "Asian technology stocks experienced volatility due to new regulatory concerns in China."
        print("--- Test 2: RAG-enabled Prompt (querying existing sample data) ---")
        # Ensure RetrieverService is running and has the sample data loaded for this test.
        # You can run services/retriever_service.py
        # The retriever agent loads data from /data/vector_store/ on startup.
        
        user_prompt_2 = "What's the news on Apple's sales?"
        response_2 = agent.generate_rag_response(
            prompt=user_prompt_2,
            use_rag=True,
            top_k_retrieval=2
            # system_prompt="You are a financial analyst summarizing information." # Override default
        )
        print(f"User Prompt 2: {user_prompt_2}")
        print(f"LLM Response 2 (RAG): {response_2}\n")

        user_prompt_2b = "Tell me about Asian technology stocks."
        response_2b = agent.generate_rag_response(
            prompt=user_prompt_2b,
            use_rag=True,
            top_k_retrieval=1
            # system_prompt="You are a market analyst." # Override default
        )
        print(f"User Prompt 2b: {user_prompt_2b}")
        print(f"LLM Response 2b (RAG): {response_2b}\n")


        # Test 2c: Specific financial query structure
        print("--- Test 2c: Specific Financial Query (RAG) ---")
        financial_query = "What’s our risk exposure in Asia tech stocks today, and highlight any earnings surprises for Apple?"
        # This query will use DEFAULT_FINANCIAL_SYSTEM_PROMPT
        # The context retrieval will use the full query: "What’s our risk exposure in Asia tech stocks today, and highlight any earnings surprises for Apple?"
        # The LLM will then be prompted with this query, augmented by any retrieved context, and guided by DEFAULT_FINANCIAL_SYSTEM_PROMPT.
        
        response_2c = agent.generate_rag_response(
            prompt=financial_query,
            use_rag=True,
            top_k_retrieval=3 # Fetch more context for complex queries
        )
        print(f"User Prompt 2c: {financial_query}")
        print(f"LLM Response 2c (RAG): {response_2c}\n")


        # Test 3: RAG-enabled prompt for a topic likely NOT in the small sample vector store
        print("--- Test 3: RAG-enabled Prompt (topic likely not in sample vector store) ---")
        user_prompt_3 = "Tell me about the history of the Roman Empire."
        response_3 = agent.generate_rag_response(
            prompt=user_prompt_3,
            use_rag=True
            # system_prompt="You are a historian." # Override default
        )
        print(f"User Prompt 3: {user_prompt_3}")
        print(f"LLM Response 3 (RAG): {response_3}\n")
        
        # Test 4: RAG explicitly disabled
        print("--- Test 4: RAG explicitly disabled ---")
        user_prompt_4 = "What are the latest developments in AI, without checking the knowledge base?"
        response_4 = agent.generate_rag_response(
            prompt=user_prompt_4,
            use_rag=False, # Explicitly disable RAG
            system_prompt="You are a tech enthusiast." # Override default
        )
        print(f"User Prompt 4: {user_prompt_4}")
        print(f"LLM Response 4 (RAG disabled): {response_4}\n")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
        import traceback
        traceback.print_exc()

