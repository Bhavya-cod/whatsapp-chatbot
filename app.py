import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

# Twilio Credentials from Environment Variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

app = Flask(__name__)

# Load the dataset
file_path = "pesticides.xlsx"
data_sheets = {}
if os.path.exists(file_path):
    xls = pd.ExcelFile(file_path)
    data_sheets = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

# Language dictionary
responses = {
    "en": {
        "greeting": "👋 Hello farmer! Reply with your language: \n1️⃣ English \n2️⃣ తెలుగు",
        "ask_crop": "🌱 Enter your crop name:",
        "ask_category": "📂 Select a pesticide category (reply with number):",
        "ask_pesticide1": "📌 Select a pesticide (reply with name):",
        "ask_pesticide2": "📌 Select another pesticide (reply with name):",
        "compatibility": "🧪 {} and {} are *{}*.",
        "no_data": "⚠️ No compatibility data found for this combination.",
        "restart": "🔄 Type *restart* to check another combination.",
    },
    "te": {
        "greeting": "👋 హలో రైతు! మీ భాషను ఎంచుకోండి: \n1️⃣ English \n2️⃣ తెలుగు",
        "ask_crop": "🌱 మీ పంట పేరు నమోదు చేయండి:",
        "ask_category": "📂 పురుగుమందుల వర్గాన్ని ఎంచుకోండి (సంఖ్యతో రిప్లై చేయండి):",
        "ask_pesticide1": "📌 ఒక పురుగుమందును ఎంచుకోండి (పేరు రిప్లై చేయండి):",
        "ask_pesticide2": "📌 మరో పురుగుమందును ఎంచుకోండి (పేరు రిప్లై చేయండి):",
        "compatibility": "🧪 {} మరియు {} *{}* గా ఉన్నాయి.",
        "no_data": "⚠️ ఈ కలయికకు డేటా లేదు.",
        "restart": "🔄 మరో కలయికను పరీక్షించడానికి *restart* టైప్ చేయండి.",
    }
}

user_sessions = {}

@app.route("/")
def home():
    return "Pesticide Chatbot is Running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if sender not in user_sessions:
        user_sessions[sender] = {"step": "language"}

    session = user_sessions[sender]
    resp = MessagingResponse()
    msg = resp.message()

    if session["step"] == "language":
        if incoming_msg in ["1", "2"]:
            lang = "en" if incoming_msg == "1" else "te"
            session["lang"] = lang
            session["step"] = "crop"
            msg.body(responses[lang]["ask_crop"])
        else:
            msg.body(responses["en"]["greeting"])

    elif session["step"] == "crop":
        session["crop"] = incoming_msg
        session["step"] = "category"
        categories = list(data_sheets.keys()) if data_sheets else []
        session["categories"] = categories
        if categories:
            msg.body(responses[session["lang"]]["ask_category"] + "\n" + 
                     "\n".join([f"{i+1}. {c}" for i, c in enumerate(categories)]))
        else:
            msg.body("⚠️ No pesticide data available. Please upload `pesticides.xlsx`.")

    elif session["step"] == "category":
        try:
            index = int(incoming_msg) - 1
            if 0 <= index < len(session["categories"]):
                session["selected_sheet"] = session["categories"][index]
                session["step"] = "pesticide1"
                df = data_sheets[session["selected_sheet"]]
                session["pesticides1"] = df.iloc[:, 1].dropna().unique().tolist()
                msg.body(responses[session["lang"]]["ask_pesticide1"] + "\n" + 
                         "\n".join(session["pesticides1"]))
            else:
                msg.body(responses[session["lang"]]["ask_category"])
        except ValueError:
            msg.body(responses[session["lang"]]["ask_category"])

    elif session["step"] == "pesticide1":
        if incoming_msg in session["pesticides1"]:
            session["pesticide1"] = incoming_msg
            session["step"] = "pesticide2"
            df = data_sheets[session["selected_sheet"]]
            session["pesticides2"] = df.iloc[:, 2].dropna().unique().tolist()
            msg.body(responses[session["lang"]]["ask_pesticide2"] + "\n" + 
                     "\n".join(session["pesticides2"]))
        else:
            msg.body(responses[session["lang"]]["ask_pesticide1"])

    elif session["step"] == "pesticide2":
        if incoming_msg in session["pesticides2"]:
            session["pesticide2"] = incoming_msg
            session["step"] = "restart"
            df = data_sheets[session["selected_sheet"]]
            match = df[(df.iloc[:, 1] == session["pesticide1"]) & 
                       (df.iloc[:, 2] == session["pesticide2"])]
            if not match.empty:
                compatibility = match.iloc[0, 3]
                msg.body(responses[session["lang"]]["compatibility"].format(
                    session["pesticide1"], session["pesticide2"], compatibility))
            else:
                msg.body(responses[session["lang"]]["no_data"])
            msg.body(responses[session["lang"]]["restart"])
        else:
            msg.body(responses[session["lang"]]["ask_pesticide2"])

    elif session["step"] == "restart" and incoming_msg.lower() == "restart":
        session["step"] = "category"
        msg.body(responses[session["lang"]]["ask_category"] + "\n" + 
                 "\n".join([f"{i+1}. {c}" for i, c in enumerate(session["categories"])]))

    return str(resp)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))  # Default to 5000
    app.run(host="0.0.0.0", port=PORT, debug=True)
