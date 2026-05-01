import os
import logging
import zipfile
from datetime import datetime

# Configure logging
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log.txt")

logger = logging.getLogger("TriageAgent")
logger.setLevel(logging.INFO)

# File handler to append cleanly to the global log.txt
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_ticket_execution(ticket_id, text, domain, req_type, risk_score, snippets, action, response):
    timestamp = datetime.now().astimezone().isoformat()
    log_msg = (
        f"## [{timestamp}] Ticket Processed: {ticket_id}\n"
        f"Ticket Text: {text}\n"
        f"Identified Domain: {domain} | Request Type: {req_type} | Risk Score: {risk_score}\n"
        f"Retrieved Context Snippets (First 100 chars each):\n{snippets}\n"
        f"Final Action: {action}\n"
        f"Generated Response: {response}\n"
    )
    logger.info(log_msg)

def create_submission():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    code_dir = os.path.join(base_dir, "code")
    zip_path = os.path.join(base_dir, "submission.zip")
    
    ignore_dirs = {".venv", "venv", "env", "__pycache__", "data", "support_issues", "support_tickets", "chroma_db", ".git"}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(code_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file.endswith('.pyc') or file == '.env':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, arcname)
    print(f"Submission created successfully at {zip_path}")
