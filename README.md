# 💰 Smart Indian Credit Card Advisor (87+ Cards)

Your intelligent assistant for discovering the best Indian credit cards based on **real annual savings** and **ROI calculations**.

---

## 🚀 Quick Launch

Run the application with a single command:

```powershell
streamlit run app.py
```

Opens at: **http://localhost:8501** (or next available port)

---

## ✨ Features

- 📊 **87+ Credit Cards**: Comprehensive database with joining/annual fees, features, and eligibility.
- 💰 **Savings Calculator**: Calculates exactly how much you'll save based on your specific spending.
- 📈 **ROI Analysis**: Shows the return on your annual fee (e.g., "750% ROI").
- ⏱️ **Break-even Tracking**: Tells you how many months it takes to recover the annual fee.
- 🧩 **Multi-Card Strategy**: Explains how to use two cards together for maximum combined savings.
- 🧠 **AI-Powered Follow-up**: Ask specific questions like "Which card for Myntra?" or "Best card for Zomato?".

---

## 📁 Project Structure

```text
/
├── data/                    # Database and source PDF
│   ├── Credit_CardDetail.pdf     # Source data
│   ├── credit_cards.json        # Unified 87-card database
│   └── educational_content.json  # "How to choose" logic
├── docs/                    # Detailed user guides
│   └── SMART_ADVISOR_GUIDE.md
├── scripts/                 # Tools and maintenance
│   ├── extract_new_pdf.py       # PDF extraction logic
│   └── create_vector_db.py      # Vector DB generator
├── app.py                   # Main Streamlit Application
├── .env                     # API Keys (GROQ_API_KEY)
├── requirements.txt         # Dependencies
└── README.md                # This guide
```

---

## 🔧 Installation

1. **Clone the project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Add your Groq API key to the `.env` file:
   ```text
   GROQ_API_KEY=your_key_here
   ```

---

## 💡 How it Works

1. **Step 1: Income** - Bot checks eligibility based on your monthly take-home.
2. **Step 2: Spending** - You provide specific amounts (e.g., "Fuel 10000, shopping 5000").
3. **Step 3: Lifestyle** - Answer questions about travel and airport lounge needs.
4. **Step 4: Analysis** - Get ranked recommendations showing **real Rs. savings**.

---

## 📞 Support & Maintenance

To update the database with a newer PDF:
1. Place the new PDF in `data/`.
2. Update the filename in `scripts/extract_new_pdf.py`.
3. Run: `python scripts/extract_new_pdf.py`.

---

🎉 **Ready to save thousands of rupees on your credit card spends!**
