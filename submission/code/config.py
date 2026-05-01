import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHAT_MODEL = "openai/gpt-oss-120b"

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chroma_db")
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_CSV = os.path.join(BASE_DIR, "support_tickets", "support_tickets.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "support_tickets", "output.csv")
