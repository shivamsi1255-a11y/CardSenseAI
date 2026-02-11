"""
Extract 90+ Credit Cards from Credit_CardDetail.pdf
Enhanced extraction with educational content and improved data structure
"""

import json
import pypdf
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
import os
import re

load_dotenv()

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    print(f"[INFO] Reading PDF: {pdf_path}")
    reader = pypdf.PdfReader(pdf_path)
    
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        full_text += f"\n--- Page {i+1} ---\n{text}"
    
    print(f"[SUCCESS] Extracted {len(reader.pages)} pages")
    return full_text

def extract_educational_content(pdf_text):
    """Extract educational content about choosing credit cards"""
    print("\n[INFO] Extracting educational content...")
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    prompt = f"""Extract educational content about choosing credit cards from this text.

Text:
{pdf_text[:20000]}

Extract sections like:
- How to Choose the Best Credit Card
- Annual/Joining Fees explanation
- APR explanation
- Reward Structure info
- Lifestyle Compatibility tips
- Credit Score Requirements

Return as JSON:
{{
  "title": "How to Choose the Best Credit Card",
  "sections": [
    {{
      "heading": "Annual/Joining Fees",
      "content": "explanation..."
    }}
  ]
}}

Return ONLY the JSON object.
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"[WARNING] Could not extract educational content: {e}")
        return None

def parse_credit_cards_enhanced(pdf_text):
    """Parse credit cards with enhanced format"""
    print("\n[INFO] Parsing credit card data using AI...")
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    prompt = f"""Extract ALL credit card information from this document and return ONLY a valid JSON array.

PDF Text:
{pdf_text}

For each card, extract:
- id: lowercase slug (e.g., "sbi-cashback")
- card_name: Full official name
- joining_fee: Number (0 if free)
- annual_fee: Number (0 if free)
- min_income_req: Estimated minimum income (default 25000 if not specified)
- short_description: Brief description
- key_features: Array of feature strings
- ideal_for: Who is this card best for
- primary_tags: Array of categories (Cashback, Travel, Fuel, Shopping, etc.)
- best_feature: Main highlight
- airport_lounge: true/false
- source: Website URL

Return ONLY JSON array:
[
  {{
    "id": "sbi-cashback",
    "card_name": "SBI Cashback Credit Card",
    "joining_fee": 999,
    "annual_fee": 999,
    "min_income_req": 30000,
    "short_description": "Cashback card for online shoppers",
    "key_features": ["5% cashback online", "1% cashback offline"],
    "ideal_for": "Frequent online shoppers",
    "primary_tags": ["Cashback", "Online Shopping"],
    "best_feature": "5% cashback on online transactions",
    "airport_lounge": false,
    "source": "https://www.sbicard.com"
  }}
]

CRITICAL: Return ONLY the JSON array, no other text.
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def save_database(cards, educational_content, cards_path="data/credit_cards.json", edu_path="data/educational_content.json"):
    """Save cards and educational content"""
    
    # Save cards
    print(f"\n[INFO] Saving credit cards to {cards_path}...")
    with open(cards_path, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"[SUCCESS] Saved {len(cards)} cards")
    
    # Save educational content
    if educational_content:
        print(f"[INFO] Saving educational content to {edu_path}...")
        with open(edu_path, 'w', encoding='utf-8') as f:
            json.dump(educational_content, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] Saved educational content")
    
    return cards

def main():
    pdf_path = "data/Credit_CardDetail.pdf"
    
    # Step 1: Extract text
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # Save for reference
    with open("data/extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(pdf_text)
    print("[INFO] Saved extracted text")
    
    # Step 2: Extract educational content
    educational_content = extract_educational_content(pdf_text)
    
    # Step 3: Parse cards in chunks
    chunk_size = 40000
    all_cards = []
    
    for i in range(0, len(pdf_text), chunk_size):
        chunk = pdf_text[i:i+chunk_size]
        print(f"\n[INFO] Processing chunk {i//chunk_size + 1}...")
        
        try:
            cards_json = parse_credit_cards_enhanced(chunk)
            clean_json = cards_json.strip().replace('```json', '').replace('```', '').strip()
            
            # Extract JSON array
            start = clean_json.find('[')
            end = clean_json.rfind(']') + 1
            if start != -1 and end > start:
                clean_json = clean_json[start:end]
            
            cards = json.loads(clean_json)
            all_cards.extend(cards if isinstance(cards, list) else [cards])
            print(f"[SUCCESS] Found {len(cards) if isinstance(cards, list) else 1} cards")
        except Exception as e:
            print(f"[WARNING] Error processing chunk: {e}")
            continue
    
    # Remove duplicates
    unique_cards = []
    seen_ids = set()
    for card in all_cards:
        card_id = card.get('id', card.get('card_name', '').lower().replace(' ', '-'))
        if card_id not in seen_ids:
            # Ensure all required fields
            if 'id' not in card:
                card['id'] = card_id
            if 'min_income_req' not in card:
                card['min_income_req'] = 25000
            if 'primary_tags' not in card:
                card['primary_tags'] = []
            if 'best_feature' not in card:
                card['best_feature'] = card.get('short_description', '')
            if 'airport_lounge' not in card:
                card['airport_lounge'] = False
            
            unique_cards.append(card)
            seen_ids.add(card_id)
    
    print(f"\n[INFO] Total unique cards: {len(unique_cards)}")
    
    # Save
    if unique_cards:
        saved_cards = save_database(unique_cards, educational_content)
        
        # Summary
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total Cards: {len(saved_cards)}")
        print(f"Free Cards (no joining fee): {sum(1 for c in saved_cards if c.get('joining_fee', 0) == 0)}")
        print(f"Lifetime Free (no annual fee): {sum(1 for c in saved_cards if c.get('annual_fee', 0) == 0)}")
        print(f"Airport Lounge Cards: {sum(1 for c in saved_cards if c.get('airport_lounge', False))}")
        
        # Fee range
        fees = [c.get('annual_fee', 0) for c in saved_cards if c.get('annual_fee', 0) > 0]
        if fees:
            print(f"Annual Fee Range: Rs.{min(fees):,} - Rs.{max(fees):,}")
        
        print("\nSample cards:")
        for card in saved_cards[:5]:
            print(f"  - {card['card_name']} (Fee: Rs.{card.get('annual_fee', 0)})")
        print("="*60)
    else:
        print("[ERROR] No cards extracted")

if __name__ == "__main__":
    main()
