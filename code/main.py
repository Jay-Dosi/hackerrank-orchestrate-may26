import pandas as pd
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from agent import SupportAgent
from utils import log_ticket_execution, create_submission
from config import INPUT_CSV, OUTPUT_CSV

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=20)
)
def process_ticket_with_backoff(agent, ticket_text):
    return agent.process_ticket(ticket_text)

def main():
    print("Loading Support Agent...")
    try:
        agent = SupportAgent()
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        return

    print(f"Loading input CSV: {INPUT_CSV}")
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"Input CSV not found at {INPUT_CSV}. Ensure ingest pipeline was run and data is present.")
        return

    results = []

    print(f"Processing {len(df)} tickets...")
    for index, row in df.iterrows():
        # Respect API Rate limits (15 RPM)
        time.sleep(4)
        
        # Handle variations in CSV schemas
        ticket_text = ""
        if "Issue" in row and pd.notna(row["Issue"]):
            ticket_text += f"Issue: {row['Issue']}\n"
        if "Subject" in row and pd.notna(row["Subject"]):
            ticket_text += f"Subject: {row['Subject']}\n"
        if "Company" in row and pd.notna(row["Company"]):
            ticket_text += f"Company (provided): {row['Company']}\n"
            
        ticket_id = f"TKT-{index + 1:03d}"

        try:
            output = process_ticket_with_backoff(agent, ticket_text)
        except Exception as e:
            print(f"Error processing ticket {ticket_id} after retries: {e}")
            output = {
                "action": "ESCALATE",
                "response": "",
                "domain": "unknown",
                "request_type": "invalid",
                "product_area": "",
                "risk_score": "High",
                "justification": "Error processing ticket.",
                "snippets": ""
            }

        # Audit Logging
        log_ticket_execution(
            ticket_id=ticket_id,
            text=ticket_text.strip(),
            domain=output["domain"],
            req_type=output["request_type"],
            risk_score=output["risk_score"],
            snippets=output["snippets"],
            action=output["action"],
            response=output["response"]
        )

        # Build output record
        results.append({
            "issue": row.get("Issue", ""),
            "subject": row.get("Subject", ""),
            "company": row.get("Company", ""),
            "response": output["response"],
            "product_area": output["product_area"],
            "status": "replied" if output["action"] == "REPLY" else "escalated",
            "request_type": output["request_type"],
            "justification": output.get("justification", "")
        })
        print(f"Processed {ticket_id}: Action={output['action']} (Domain: {output['domain']})")

    # Save to output
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Processing complete. Saved output to {OUTPUT_CSV}")

    # Auto package
    create_submission()

if __name__ == "__main__":
    main()
