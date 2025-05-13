import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle

# Define paths for storing the index and text data
# Assumes this script is in the 'agents' directory, and 'data' is a sibling directory
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'vector_store')
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss_index.idx")
TEXT_DATA_PATH = os.path.join(DATA_DIR, "text_data.pkl")
MODEL_NAME = 'all-MiniLM-L6-v2' # A good general-purpose model, 384 dimensions

class RetrieverAgent:
    def __init__(self, model_name=MODEL_NAME, index_path=FAISS_INDEX_PATH, text_data_path=TEXT_DATA_PATH):
        os.makedirs(DATA_DIR, exist_ok=True) # Ensure data directory exists
        
        print(f"Loading sentence transformer model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Sentence transformer model loaded.")
        
        self.index_path = index_path
        self.text_data_path = text_data_path
        self.texts = [] # To store the original text documents
        self.index = None

        self._load() # Attempt to load existing index and texts

        if self.index is None: # If loading failed or no index existed
            embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"No existing FAISS index found or failed to load. Initializing a new empty index with dimension {embedding_dim}.")
            self.index = faiss.IndexFlatL2(embedding_dim)
        # self.texts would have been loaded or initialized as [] by _load()

    def add_texts(self, new_texts: list[str]):
        if not new_texts:
            print("No new texts to add.")
            return

        print(f"Generating embeddings for {len(new_texts)} new text(s)...")
        # show_progress_bar=True can be helpful for large batches
        embeddings = self.model.encode(new_texts, convert_to_tensor=False, show_progress_bar=False) 
        embeddings_np = np.array(embeddings).astype('float32') # FAISS expects float32

        print(f"Adding {embeddings_np.shape[0]} embedding(s) to FAISS index...")
        self.index.add(embeddings_np)
        self.texts.extend(new_texts)
        print(f"Index now contains {self.index.ntotal} embeddings. Total texts stored: {len(self.texts)}.")
        self._save() # Save after adding

    def search(self, query: str, top_k: int = 5):
        print(f"[RetrieverAgent.search] Method called with query: \"{query}\", k_param: {top_k} (type: {type(top_k)})")

        if not isinstance(top_k, int) or top_k <= 0:
            # This case should ideally be caught by Pydantic validation if called via service (gt=0)
            # or if k is not sent in request, SearchQueryRequest defaults to 5.
            print(f"[RetrieverAgent.search] Warning: k_param ({top_k}) is not a positive integer. Using default k=5 for this search operation.")
            top_k = 5
        
        if self.index is None:
            print("[RetrieverAgent.search] Error: FAISS index is None. Cannot perform search.")
            return []
        
        if self.index.ntotal == 0:
            print("[RetrieverAgent.search] Index is empty (ntotal is 0). No results to return.")
            return []

        print(f"[RetrieverAgent.search] Generating embedding for query: \"{query}\"")
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        query_embedding_np = np.array(query_embedding).astype('float32')
        
        k_for_faiss_search = top_k 

        print(f"[RetrieverAgent.search] About to call faiss_index.search with k_for_faiss_search = {k_for_faiss_search}.")
        print(f"[RetrieverAgent.search] Current index.ntotal = {self.index.ntotal}.")

        # FAISS will return min(k_for_faiss_search, self.index.ntotal) results
        distances, indices = self.index.search(query_embedding_np, k_for_faiss_search)

        results = []
        if indices.size > 0 and len(indices[0]) > 0: # Check if FAISS returned any indices
            num_results_returned_by_faiss = len(indices[0])
            # If indices[0][0] == -1, it means no neighbors found for that k (should not happen with IndexFlatL2 unless k=0 or index empty)
            if num_results_returned_by_faiss == 1 and indices[0][0] == -1:
                print(f"[RetrieverAgent.search] faiss_index.search returned indices[0][0] == -1, indicating no results found for k_for_faiss_search = {k_for_faiss_search}.")
                num_results_returned_by_faiss = 0 # Treat as no results
            else:
                print(f"[RetrieverAgent.search] faiss_index.search returned {num_results_returned_by_faiss} result(s) for k_for_faiss_search = {k_for_faiss_search}.")

            # Iterate based on what FAISS actually returned
            for i in range(num_results_returned_by_faiss): 
                idx = indices[0][i]
                if idx == -1: # Should not happen if we checked above, but as safeguard
                    continue 
                
                if 0 <= idx < len(self.texts):
                    results.append({
                        "text": self.texts[idx],
                        "distance": float(distances[0][i]),
                        "id": int(idx) 
                    })
                else:
                    print(f"[RetrieverAgent.search] Warning: FAISS returned index {idx} which is out of bounds for self.texts (len: {len(self.texts)}). This text will be skipped.")
        else:
            print(f"[RetrieverAgent.search] faiss_index.search returned no results (indices.size is 0 or len(indices[0]) is 0).")
        
        print(f"[RetrieverAgent.search] Method returning {len(results)} results.")
        return results

    def _save(self):
        if self.index:
            print(f"Saving FAISS index to {self.index_path} ({self.index.ntotal} embeddings)")
            faiss.write_index(self.index, self.index_path)
        
        print(f"Saving text data to {self.text_data_path} ({len(self.texts)} texts)")
        with open(self.text_data_path, 'wb') as f:
            pickle.dump(self.texts, f)
        print("Save complete.")

    def _load(self):
        # Load FAISS index
        if os.path.exists(self.index_path):
            try:
                print(f"Loading FAISS index from {self.index_path}...")
                self.index = faiss.read_index(self.index_path)
                print(f"FAISS index loaded successfully with {self.index.ntotal} embeddings.")
            except Exception as e:
                print(f"Error loading FAISS index from {self.index_path}: {e}. Will create a new one if texts are added.")
                self.index = None 
        else:
            print(f"FAISS index file not found at {self.index_path}. A new index will be created if texts are added.")
            self.index = None

        # Load text data
        if os.path.exists(self.text_data_path):
            try:
                print(f"Loading text data from {self.text_data_path}...")
                with open(self.text_data_path, 'rb') as f:
                    self.texts = pickle.load(f)
                print(f"Text data loaded successfully with {len(self.texts)} documents.")
            except Exception as e:
                print(f"Error loading text data from {self.text_data_path}: {e}. Initializing with empty list.")
                self.texts = []
        else:
            print(f"Text data file not found at {self.text_data_path}. Initializing with empty list.")
            self.texts = []
            
        # Sanity check: if index is loaded but texts are not, or vice-versa in a way that's inconsistent
        if self.index is not None and self.index.ntotal != len(self.texts):
            print(f"Warning: Mismatch between FAISS index size ({self.index.ntotal}) and loaded texts ({len(self.texts)}). Re-initializing.")
            self.index = None
            self.texts = []


    def get_status(self):
        status = f"Model: {MODEL_NAME}\n"
        if self.index:
            status += f"FAISS Index: Initialized, {self.index.ntotal} embeddings.\n"
        else:
            status += "FAISS Index: Not initialized or empty.\n"
        status += f"Text Documents: {len(self.texts)} stored."
        return status

if __name__ == '__main__':
    print("--- Initializing RetrieverAgent ---")
    retriever = RetrieverAgent()
    print(f"--- RetrieverAgent Status ---\n{retriever.get_status()}\n-----------------------------")

    sample_documents = [
        "Apple Inc. reported a significant increase in iPhone sales during the last quarter.",
        "Microsoft Azure continues to show strong growth in the cloud computing market.",
        "Google's DeepMind announced a breakthrough in protein folding.",
        "Asian technology stocks experienced volatility due to new regulatory concerns in China.",
        "TSMC is expanding its chip manufacturing capacity to meet global demand.",
        "Samsung unveiled its latest foldable smartphone with enhanced durability.",
        "The Federal Reserve hinted at potential changes to interest rates next month.",
        "A global semiconductor shortage is impacting car manufacturers and electronics companies."
    ]

    # Simple check to avoid re-adding identical sample docs if index already has them
    # A more robust system would use document IDs or content hashing.
    if not retriever.texts or not all(doc in retriever.texts for doc in sample_documents):
        print("\n--- Adding Sample Documents ---")
        # For a clean demo, you might want to clear existing data first if re-running:
        # if os.path.exists(FAISS_INDEX_PATH): os.remove(FAISS_INDEX_PATH)
        # if os.path.exists(TEXT_DATA_PATH): os.remove(TEXT_DATA_PATH)
        # retriever = RetrieverAgent() # Re-initialize
        retriever.add_texts(sample_documents)
        print(f"--- RetrieverAgent Status after adding docs ---\n{retriever.get_status()}\n-----------------------------")
    else:
        print("\n--- Sample documents appear to be already indexed ---")

    queries_to_test = [
        "latest news about Apple",
        "developments in Asian tech market",
        "impact of interest rates on tech",
        "chip manufacturing updates"
    ]

    print("\n--- Performing Searches ---")
    for query in queries_to_test:
        print(f"\nSearching for: '{query}' (top 2 results)")
        search_results = retriever.search(query, top_k=2)
        if search_results:
            for result in search_results:
                print(f"  ID: {result['id']}, Distance: {result['distance']:.4f}")
                print(f"  Text: \"{result['text']}\"")
        else:
            print("  No results found.")
    print("---------------------------")
