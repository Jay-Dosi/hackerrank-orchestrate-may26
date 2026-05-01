import json
import re
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from config import CHAT_MODEL, EMBEDDING_MODEL, CHROMA_DB_DIR
from prompts import ROUTER_PROMPT, GENERATOR_PROMPT

class SupportAgent:
    def __init__(self):
        self.llm = ChatGroq(model_name=CHAT_MODEL, temperature=0.0)
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        
        # Load the Chroma DB
        self.db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=self.embeddings)
        
        self.router_chain = ROUTER_PROMPT | self.llm
        self.generator_chain = GENERATOR_PROMPT | self.llm

    def process_ticket(self, ticket_text):
        # Node 1: Classify
        try:
            router_response = self.router_chain.invoke({"ticket_text": ticket_text})
            json_str = router_response.content
            
            # Cleanup markdown block if present
            if "```json" in json_str:
                json_str = re.search(r'```json\n(.*)\n```', json_str, re.DOTALL).group(1)
            elif "```" in json_str:
                json_str = re.search(r'```\n(.*)\n```', json_str, re.DOTALL).group(1)
                
            parsed = json.loads(json_str)
            domain = parsed.get("domain", "unknown").lower()
            risk_score = parsed.get("risk_score", "High")
            req_type = parsed.get("request_type", "invalid")
            product_area = parsed.get("product_area", "")
            justification = parsed.get("justification", "Escalated due to uncertainty or high risk.")
        except Exception as e:
            print(f"Classification failed: {e}")
            domain = "unknown"
            risk_score = "High"
            req_type = "invalid"
            product_area = ""
            justification = "Failed to classify ticket."

        # Node 2: Gatekeeper Check
        if risk_score.lower() == "high" or domain == "unknown":
            return {
                "action": "ESCALATE",
                "response": "",
                "domain": domain,
                "request_type": req_type,
                "product_area": product_area,
                "risk_score": risk_score,
                "justification": justification,
                "snippets": ""
            }

        # Node 3: Isolated Retrieval
        try:
            retriever = self.db.as_retriever(
                search_kwargs={"k": 4, "filter": {"domain": domain}}
            )
            retrieved_docs = retriever.invoke(ticket_text)
            
            snippets = "\n".join([f"- {doc.page_content[:100]}..." for doc in retrieved_docs])
            context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        except Exception as e:
            print(f"Retrieval failed: {e}")
            context = ""
            snippets = ""

        # Node 4: Grounded Generation
        try:
            gen_response = self.generator_chain.invoke({
                "context": context,
                "ticket_text": ticket_text
            })
            generated_text = gen_response.content.strip()

            if generated_text == "ESCALATE":
                return {
                    "action": "ESCALATE",
                    "response": "",
                    "domain": domain,
                    "request_type": req_type,
                    "product_area": product_area,
                    "risk_score": risk_score,
                    "justification": "Escalated because no exact answer found or human intervention required.",
                    "snippets": snippets
                }
            else:
                return {
                    "action": "REPLY",
                    "response": generated_text,
                    "domain": domain,
                    "request_type": req_type,
                    "product_area": product_area,
                    "risk_score": risk_score,
                    "justification": justification,
                    "snippets": snippets
                }
        except Exception as e:
            print(f"Generation failed: {e}")
            return {
                "action": "ESCALATE",
                "response": "",
                "domain": domain,
                "request_type": req_type,
                "product_area": product_area,
                "risk_score": risk_score,
                "justification": "Generation error.",
                "snippets": snippets
            }
