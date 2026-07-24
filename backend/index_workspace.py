from agents.vector_store import OllamaEmbeddings, LocalVectorStore, index_workspace
from config import DEFAULT_MAIN_MODEL

def main():
    print("Starting workspace indexing...")
    embedder = OllamaEmbeddings(model_name=DEFAULT_MAIN_MODEL)
    store = LocalVectorStore()
    index_workspace(embedder, store)
    print("Indexing completed successfully.")

if __name__ == "__main__":
    main()
