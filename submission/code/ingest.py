import os
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from config import DATA_DIR, CHROMA_DB_DIR, GEMINI_API_KEY, EMBEDDING_MODEL

def populate_db():
    if os.path.exists(CHROMA_DB_DIR):
        print("Vector database already exists. Skipping ingestion.")
        return

    print("Initializing Vector Database ingestion...")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing from environment variables.")

    documents = []
    
    # Iterate through subdirectories in data/
    for domain in os.listdir(DATA_DIR):
        domain_path = os.path.join(DATA_DIR, domain)
        if os.path.isdir(domain_path):
            # Load all text or markdown files in the domain folder
            loader = DirectoryLoader(domain_path, glob="**/*.*", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}, use_multithreading=True, show_progress=True)
            domain_docs = loader.load()
            
            # Tag metadata strictly
            for doc in domain_docs:
                doc.metadata["domain"] = domain
            
            documents.extend(domain_docs)

    print(f"Loaded {len(documents)} documents across domains.")

    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    # Embed and store
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
    
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}...")
        
        @retry(
            stop=stop_after_attempt(10),
            wait=wait_exponential(multiplier=1, min=2, max=30)
        )
        def add_batch():
            db.add_documents(batch)
            
        add_batch()
        # Sleep to avoid aggressively triggering 429s
        time.sleep(1)

    if hasattr(db, 'persist'):
        db.persist()
    print("Vector database populated and persisted.")

if __name__ == "__main__":
    populate_db()
