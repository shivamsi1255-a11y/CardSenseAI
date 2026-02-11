"""
Vector Database Creation for Credit Card Chatbot
This script creates embeddings from credit card data and stores them in a FAISS vector database
"""

import json
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

def load_credit_cards():
    """Load credit card data from JSON file"""
    with open("data/credit_cards.json", "r", encoding="utf-8") as f:
        return json.load(f)

def create_documents_from_cards(credit_cards):
    """Convert credit card data to LangChain Document objects"""
    documents = []
    
    for card in credit_cards:
        # Create a rich text representation of each card
        card_text = f"""
Card Name: {card['card_name']}
Minimum Income Requirement: ₹{card['min_income_req']:,} per month
Categories: {', '.join(card['primary_tags'])}
Best Feature: {card['best_feature']}
Annual Fee: {card['fee_type']}
Airport Lounge Access: {'Yes' if card['airport_lounge'] else 'No'}
Card ID: {card['id']}
        """.strip()
        
        # Create metadata for filtering
        metadata = {
            "card_id": card["id"],
            "card_name": card["card_name"],
            "min_income": card["min_income_req"],
            "tags": ", ".join(card["primary_tags"]),
            "fee_type": card["fee_type"],
            "airport_lounge": card["airport_lounge"]
        }
        
        documents.append(Document(page_content=card_text, metadata=metadata))
    
    return documents

def create_vector_store():
    """Create and save FAISS vector store"""
    print("Loading credit card data...")
    credit_cards = load_credit_cards()
    print(f"Loaded {len(credit_cards)} credit cards")
    
    print("\nCreating documents...")
    documents = create_documents_from_cards(credit_cards)
    print(f"Created {len(documents)} documents")
    
    print("\nInitializing embeddings model...")
    # Using a lightweight, efficient model for embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print("Creating vector store...")
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Create directory if it doesn't exist
    os.makedirs("data/vectorstore", exist_ok=True)
    
    print("Saving vector store...")
    vector_store.save_local("data/vectorstore")
    
    print("\n✅ Vector store created successfully!")
    print(f"📁 Saved to: data/vectorstore/")
    print(f"📊 Total embeddings: {len(documents)}")
    
    # Test the vector store
    print("\n🧪 Testing vector store...")
    test_query = "Which card is best for travel?"
    results = vector_store.similarity_search(test_query, k=3)
    print(f"\nQuery: '{test_query}'")
    print("\nTop 3 results:")
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. {doc.metadata['card_name']}")
        print(f"   Score relevance: {doc.metadata['tags']}")

if __name__ == "__main__":
    create_vector_store()
