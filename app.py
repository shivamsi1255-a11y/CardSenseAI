import os
import json
import re
import uuid
import textwrap
from flask import Flask, render_template, request, jsonify, session
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", str(uuid.uuid4()))

# Load credit card data
def load_credit_cards():
    data_path = os.path.join(os.path.dirname(__file__), "data", "credit_cards.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)

CREDIT_CARDS = load_credit_cards()

# ─── Chatbot Logic (reused from app.py) ───────────────────────────────────────

class FinancialCreditCardChatbot:
    def __init__(self, state=None):
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.model_name = "llama-3.3-70b-versatile"
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=0.7,
            max_tokens=1024,
            api_key=self.groq_api_key,
        )
        if state:
            self.user_profile = state["user_profile"]
            self.conversation_stage = state["conversation_stage"]
            self.cards_with_savings = state.get("cards_with_savings", [])
        else:
            self.user_profile = {
                "income": None,
                "spending": {
                    "fuel": 0, "shopping": 0, "online": 0, "bills": 0,
                    "dining": 0, "groceries": 0, "travel": 0, "other": 0
                },
                "lounge_access": None
            }
            self.conversation_stage = 0
            self.cards_with_savings = []

    def get_state(self):
        return {
            "user_profile": self.user_profile,
            "conversation_stage": self.conversation_stage,
            "cards_with_savings": self.cards_with_savings,
        }

    def parse_annual_fee(self, card):
        if 'annual_fee' in card:
            return card['annual_fee']
        fee_type = card.get('fee_type', '')
        if "Lifetime Free" in fee_type or "Free" in fee_type:
            return 0
        match = re.search(r'(\d+)', fee_type)
        if match:
            return int(match.group(1))
        return 500

    def get_cashback_rate(self, card, category):
        tags = [tag.lower() for tag in card['primary_tags']]
        feature = card['best_feature'].lower()
        category = category.lower()
        cashback_match = re.search(r'(\d+\.?\d*)%', feature)
        default_rate = float(cashback_match.group(1)) if cashback_match else 1.0
        category_keywords = {
            'fuel': ['fuel', 'petrol', 'diesel', 'bpcl', 'hpcl', 'indianoil'],
            'shopping': ['shopping', 'retail', 'flipkart', 'amazon', 'myntra'],
            'online': ['online', 'flipkart', 'amazon', 'swiggy', 'zomato'],
            'bills': ['bills', 'utility', 'recharge', 'payment', 'electricity', 'water', 'gas', 'mobile'],
            'dining': ['dining', 'restaurant', 'zomato', 'swiggy', 'food'],
            'groceries': ['grocery', 'groceries', 'supermarket', 'departmental'],
            'travel': ['travel', 'flight', 'hotel', 'booking', 'international', 'plane', 'train', 'irctc']
        }
        for tag in tags:
            if any(keyword in tag for keyword in category_keywords.get(category, [])):
                return default_rate
        if any(keyword in feature for keyword in category_keywords.get(category, [])):
            return default_rate
        if 'universal' in ' '.join(tags) or 'all spends' in feature:
            return default_rate
        return 0.25 if category != 'other' else 0.1

    def calculate_savings(self, card):
        annual_benefits = 0
        breakdown = {}
        for category, monthly_amount in self.user_profile['spending'].items():
            if monthly_amount > 0:
                annual_amount = monthly_amount * 12
                cashback_rate = self.get_cashback_rate(card, category)
                benefit = annual_amount * (cashback_rate / 100)
                if benefit > 0:
                    breakdown[category] = {
                        "spending": annual_amount,
                        "rate": cashback_rate,
                        "benefit": benefit
                    }
                    annual_benefits += benefit
        annual_fee = self.parse_annual_fee(card)
        if self.user_profile['lounge_access'] and card['airport_lounge']:
            annual_benefits += 2000
            breakdown['lounge_access'] = {"spending": 0, "rate": 0, "benefit": 2000}
        net_savings = annual_benefits - annual_fee
        roi = (net_savings / annual_fee * 100) if annual_fee > 0 else float('inf')
        return {
            "annual_benefits": annual_benefits,
            "annual_fee": annual_fee,
            "net_savings": net_savings,
            "roi": roi,
            "breakdown": breakdown
        }

    def filter_and_rank_cards(self):
        if self.user_profile["income"] is None:
            return []
        eligible_cards = [
            card for card in CREDIT_CARDS
            if card["min_income_req"] <= self.user_profile["income"]
        ]
        cards_with_savings = []
        for card in eligible_cards:
            savings_calc = self.calculate_savings(card)
            if savings_calc['net_savings'] > 0:
                cards_with_savings.append({
                    'card': card,
                    'savings': savings_calc
                })
        cards_with_savings.sort(key=lambda x: x['savings']['net_savings'], reverse=True)
        return cards_with_savings[:3]

    def format_savings_recommendation(self, cards_with_savings):
        if not cards_with_savings:
            return "Unfortunately, none of the cards would give you positive savings based on your spending pattern. Consider increasing usage in rewarding categories."
        
        total_spending = sum(self.user_profile['spending'].values()) * 12
        
        # HTML Response Builder - Flattened HTML to avoid Markdown parsing issues
        response = f'<div class="analysis-header"><h2>💰 Financial Analysis</h2><div class="spending-summary"><span>Annual Spending</span><span class="amount">₹{total_spending:,.0f}</span></div></div><div class="cards-container">'
        
        for i, card_data in enumerate(cards_with_savings, 1):
            card = card_data['card']
            savings = card_data['savings']
            
            rank_class = "rank-1" if i == 1 else "rank-other"
            badge = "🏆 Best Choice" if i == 1 else f"Option #{i}"
            
            roi_display = "∞%" if savings['roi'] == float('inf') else f"{savings['roi']:.0f}%"
            
            # Features list
            features_html = ""
            if 'key_features' in card and card['key_features']:
                features_html = '<ul class="feature-list">' + "".join([f"<li>{f}</li>" for f in card['key_features'][:3]]) + '</ul>'

            # Breakdown table
            breakdown_html = ""
            for category, details in savings['breakdown'].items():
                cat_name = "Airport Lounge Access" if category == 'lounge_access' else category.title()
                rate_display = f"{details['rate']:.1f}%" if category != 'lounge_access' else "4 visits"
                breakdown_html += (
                    f'<tr>'
                    f'<td>{cat_name}</td>'
                    f'<td class="text-right">₹{details["spending"]:,.0f}</td>'
                    f'<td class="text-right badge-cell"><span class="rate-badge">{rate_display}</span></td>'
                    f'<td class="text-right font-bold">₹{details["benefit"]:,.0f}</td>'
                    f'</tr>'
                )

            breakeven_html = ""
            if savings['annual_fee'] > 0:
                breakeven_months = (savings['annual_fee'] / (savings['annual_benefits'] / 12)) if savings['annual_benefits'] > 0 else 0
                breakeven_html = f'<div class="breakeven-tag">⏱️ Break-even: {breakeven_months:.1f} months</div>'

            response += (
                f'<div class="recommendation-card {rank_class}">'
                f'<div class="card-header"><div class="card-title-row"><h3>{card["card_name"]}</h3><span class="rank-badge">{badge}</span></div><div class="savings-highlight"><span class="label">YOU SAVE</span><span class="value">₹{savings["net_savings"]:,.0f}<small>/year</small></span></div></div>'
                f'<div class="card-body">'
                f'<div class="stats-grid"><div class="stat-item"><span class="stat-label">ROI</span><span class="stat-value">{roi_display}</span></div><div class="stat-item"><span class="stat-label">Annual Fee</span><span class="stat-value">₹{savings["annual_fee"]:,.0f}</span></div></div>'
                f'{features_html}'
                f'<div class="breakdown-section"><h4>Benefits Breakdown</h4><table class="breakdown-table"><thead><tr><th>Category</th><th class="text-right">Spend</th><th class="text-right">Rate</th><th class="text-right">Savings</th></tr></thead><tbody>{breakdown_html}</tbody></table></div>'
                f'<div class="card-footer-info">{breakeven_html}<div class="best-feature-tag">{card["best_feature"]}</div></div>'
                f'</div></div>'
            )
        
        response += "</div>" # End cards-container
        
        # Multi-card strategy
        if len(cards_with_savings) >= 2:
            top2_savings = cards_with_savings[0]['savings']['net_savings'] + cards_with_savings[1]['savings']['net_savings']
            c1_name = cards_with_savings[0]['card']['card_name']
            c2_name = cards_with_savings[1]['card']['card_name']
            
            # Strategy Breakdown Logic
            strategy_tips = ""
            for category, amount in self.user_profile['spending'].items():
                if amount > 0:
                    s1 = cards_with_savings[0]['savings']['breakdown'].get(category, {'benefit': 0})['benefit']
                    s2 = cards_with_savings[1]['savings']['breakdown'].get(category, {'benefit': 0})['benefit']
                    
                    if s1 > s2:
                        best_card = c1_name.split()[0] # Short name
                    elif s2 > s1:
                        best_card = c2_name.split()[0]
                    else:
                         continue # Skip if equal/trivial
                    
                    strategy_tips += f"<li>{category.title()}: <strong>{best_card}</strong></li>"
            
            if strategy_tips:
                strategy_tips = f'<div class="strategy-tips"><h4>⚡ Quick Guide:</h4><ul>{strategy_tips}</ul></div>'

            response += (
                f'<div class="strategy-box">'
                f'<div class="strategy-header"><h3>💡 Power Strategy: Multi-Card Approach</h3></div>'
                f'<div class="strategy-content">'
                f'<p>Combine <strong>{c1_name}</strong> and <strong>{c2_name}</strong> to maximize rewards.</p>'
                f'{strategy_tips}'
                f'<div class="strategy-total"><span>Total Potential Settings</span><span class="strategy-amount">₹{top2_savings:,.0f}</span></div>'
                f'<p class="strategy-note">Different cards excel in different categories - use the right card for each spend!</p>'
                f'</div></div>'
            )
        
        return response

    def extract_spending_from_text(self, user_input):
        extraction_prompt = f"""Extract spending amounts from the user's message. Return as JSON.

User message: "{user_input}"

CRITICAL: If a category has multiple items, SUM them together. 
Categories to extract (MONTHLY amounts in Rupees):
- fuel
- shopping
- online (all online spending including flips/amazon/etc unless strictly another category)
- bills (utility, mobile, internet, electricity)
- dining (restaurants, food delivery)
- groceries
- travel (flights, hotels, bookings)
- other (anything else like EMI, Rent, Insurance, Fees)

Example: "fuel 3000, 5000 on flights, 2000 mobile recharge, 500 electric" 
-> {{"fuel": 3000, "travel": 5000, "bills": 2500, "other": 0, ...}}

Return ONLY JSON: {{"fuel": 0, "shopping": 0, "online": 0, "bills": 0, "dining": 0, "groceries": 0, "travel": 0, "other": 0}}
"""
        try:
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])
            content = response.content.strip().replace('```json', '').replace('```', '').strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1:
                content = content[start:end]
            return json.loads(content)
        except Exception as e:
            print(f"Extraction error: {e}")
            return {}

    def process_user_input(self, user_input):
        # Stage 0: Income
        if self.user_profile["income"] is None:
            try:
                extraction = f"""Extract monthly income from: "{user_input}"
Examples: "50000" -> 50000, "50k" -> 50000, "1 lakh" -> 100000
Return only the number."""
                response = self.llm.invoke([HumanMessage(content=extraction)])
                income_text = re.sub(r'[^0-9]', '', response.content.strip())
                if not income_text:
                    return "Please provide your monthly income as a number (e.g., 50000 or 50k)"
                income = int(income_text)
                self.user_profile["income"] = income
                return textwrap.dedent(f"""
                <div class="status-message success">
                    ✅ Income recorded: <strong>₹{income:,}/month</strong>
                </div>
                <div class="question-box">
                    <p>Now, let's analyze your spending. Please tell me your <strong>monthly expenses</strong> by category.</p>
                    <div class="example-box">
                        <span class="example-label">Example:</span>
                        "Fuel 12000, Shopping 5000, Bills 2000"
                    </div>
                </div>
                """)
            except:
                return "Please provide your monthly income as a number (e.g., 50000 or 50k)"

        # Stage 1: Spending details
        elif sum(self.user_profile['spending'].values()) == 0:
            extracted_spending = self.extract_spending_from_text(user_input)
            if extracted_spending:
                valid_extraction = False
                for category, amount in extracted_spending.items():
                    if amount > 0 and category in self.user_profile['spending']:
                        self.user_profile['spending'][category] = amount
                        valid_extraction = True
                if valid_extraction:
                    total = sum(self.user_profile['spending'].values())
                    breakdown_rows = "".join([f"<li><span>{cat.title()}</span><span>₹{amt:,}</span></li>" for cat, amt in self.user_profile['spending'].items() if amt > 0])
                    
                    return textwrap.dedent(f"""
                    <div class="status-message success">
                        ✅ Spending recorded!
                    </div>
                    <div class="spending-breakdown-card">
                        <h4>Your Monthly Breakdown</h4>
                        <ul class="spending-list">
                            {breakdown_rows}
                        </ul>
                        <div class="spending-total">
                            <span>Total</span>
                            <span>₹{total:,}/month</span>
                        </div>
                    </div>
                    <div class="question-box">
                        <p>One last question: Do you travel frequently and need <strong>Airport Lounge access</strong>?</p>
                        <div class="chip-options">
                            <span class="chip">Yes, I need it</span>
                            <span class="chip">No, not required</span>
                        </div>
                    </div>
                    """)
            return "Please tell me your monthly spending amounts, for example: 'Fuel 10000, Shopping 5000, Bills 2000'"

        # Stage 2: Lounge access
        elif self.user_profile["lounge_access"] is None:
            user_input_lower = user_input.lower()
            self.user_profile["lounge_access"] = 'yes' in user_input_lower or 'need' in user_input_lower
            self.cards_with_savings = self.filter_and_rank_cards()
            response = self.format_savings_recommendation(self.cards_with_savings)
            response += "\n\n💬 **Want to explore more options?** Ask me:\n"
            response += "- 'Explain multi-card strategy'\n"
            response += "- 'Which card is best for groceries?'\n"
            response += "- 'Show me lifetime free cards'\n"
            return response

        # Stage 3: Follow-up questions
        else:
            query = user_input.lower()
            if 'multi-card' in query or 'strategy' in query or 'explain' in query:
                if self.cards_with_savings and len(self.cards_with_savings) >= 2:
                    c1 = self.cards_with_savings[0]
                    c2 = self.cards_with_savings[1]
                    response = f"## 🧩 Detailed Multi-Card Strategy Analysis\n\n"
                    response += f"### Why this combination?\n"
                    response += f"The **{c1['card']['card_name']}** and **{c2['card']['card_name']}** are recommended together because they cover each other's weaknesses.\n\n"
                    response += "### 📊 Category-wise Optimization\n"
                    response += "Here is specifically how you should split your spending:\n\n"
                    total_benefits = 0
                    fees = c1['savings']['annual_fee'] + c2['savings']['annual_fee']
                    all_categories = set(c1['savings']['breakdown'].keys()) | set(c2['savings']['breakdown'].keys())
                    all_categories.discard('lounge_access')
                    for cat in sorted(all_categories):
                        val1 = c1['savings']['breakdown'].get(cat, {'rate': 0, 'benefit': 0})
                        val2 = c2['savings']['breakdown'].get(cat, {'rate': 0, 'benefit': 0})
                        if val1['rate'] >= val2['rate']:
                            winner = c1['card']['card_name']
                            rate = val1['rate']
                            benefit = val1['benefit']
                        else:
                            winner = c2['card']['card_name']
                            rate = val2['rate']
                            benefit = val2['benefit']
                        total_benefits += benefit
                        response += f"- **{cat.title()}**: Use **{winner}** ({rate}% cashback) → **₹{benefit:,.0f} saved**\n"
                    if self.user_profile['lounge_access']:
                        has_lounge = []
                        if c1['card']['airport_lounge']: has_lounge.append(c1['card']['card_name'])
                        if c2['card']['airport_lounge']: has_lounge.append(c2['card']['card_name'])
                        if has_lounge:
                            total_benefits += 2000
                            response += f"- **Airport Lounge**: Available on **{' & '.join(has_lounge)}** → **₹2,000 value**\n"
                    response += f"\n### 💰 Final Financial Summary\n"
                    response += f"| Metric | Amount |\n"
                    response += f"| :--- | :--- |\n"
                    response += f"| Total Annual Benefits | ₹{total_benefits:,.0f} |\n"
                    response += f"| Total Combined Fees | -₹{fees:,.0f} |\n"
                    response += f"| **NET ANNUAL SAVINGS** | **₹{total_benefits - fees:,.0f}** |\n\n"
                    response += f"💡 **Pro-Tip**: Always pay your bills through the app or platform that specific card rewards most!\n\n"
                    response += "Does this breakdown help? Would you like to check a 3rd card or restart?"
                    return response
                else:
                    return "A multi-card strategy works best when multiple cards have high rewards in different areas. Currently, one single card is dominant for your spending profile!"
            else:
                try:
                    search_prompt = f"""Based on the user's query and their profile, search the credit card database for the best recommendation.
                    
                    User Query: "{user_input}"
                    User Profile: Income ₹{self.user_profile['income']}/month, Spending: {self.user_profile['spending']}
                    
                    Available Cards: {[{'name': c['card_name'], 'features': c['best_feature'], 'tags': c['primary_tags'], 'ideal': c.get('ideal_for', '')} for c in CREDIT_CARDS[:30]]}
                    
                    Instructions:
                    1. Identify if the user is asking about a specific brand, category, or feature.
                    2. Recommend the single BEST card for that specific request from our database.
                    3. Explain WHY it is best for that specific need.
                    4. Keep it conversational and helpful.
                    5. CRITICAL: Never mention the exact number of cards in our database.
                    
                    Response Format:
                    - Best Card: [Card Name]
                    - Why: [Explanation]
                    - Savings: [Brief mention of cashback rate if known]
                    """
                    response_ai = self.llm.invoke([HumanMessage(content=search_prompt)])
                    return response_ai.content + "\n\n💬 Is there anything else you'd like to know? Or would you like to **start over** with new spending details?"
                except Exception:
                    return f"I can help with that! Would you like me to look for a specific bank or category? Or we can **start over** to recalculate everything."


# ─── Flask Routes ──────────────────────────────────────────────────────────────

INITIAL_MESSAGE = (
    "👋 Hi! I'm your **Smart Credit Card Advisor**.\n\n"
    "I'll help you find cards that will **actually save you money** — not just list features!\n\n"
    "I'll calculate:\n"
    "- 💰 Real ₹ savings per card\n"
    "- 📈 ROI on annual fees\n"
    "- ⏱️ Break-even points\n\n"
    "Let's start!\n\n"
    "**Question 1**: What is your monthly take-home income (in ₹)?"
)


@app.route("/")
def index():
    # Reset session on fresh page load
    session.clear()
    session["chatbot_state"] = None
    session["messages"] = [{"role": "assistant", "content": INITIAL_MESSAGE}]
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Restore chatbot state from session
    state = session.get("chatbot_state")
    chatbot = FinancialCreditCardChatbot(state=state)

    # Process message
    bot_response = chatbot.process_user_input(user_message)

    # Save state back to session
    session["chatbot_state"] = chatbot.get_state()

    # Append to message history
    messages = session.get("messages", [])
    messages.append({"role": "user", "content": user_message})
    messages.append({"role": "assistant", "content": bot_response})
    session["messages"] = messages

    return jsonify({"response": bot_response})


@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    session["chatbot_state"] = None
    session["messages"] = [{"role": "assistant", "content": INITIAL_MESSAGE}]
    return jsonify({"response": INITIAL_MESSAGE})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
