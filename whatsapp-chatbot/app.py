import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

app = Flask(__name__)

# Load pesticide dataset
FILE_PATH = "pesticides.xlsx"
data_sheets = {}
if os.path.exists(FILE_PATH):
    xls = pd.ExcelFile(FILE_PATH)
    data_sheets = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

# English-to-Telugu pesticide translation dictionary
pesticide_translation = {
    "Glyphosate": "గ్లైఫోసేట్",
    "Chlorpyrifos": "క్లోర్పైరిఫోస్",
    "Carbendazim": "కార్బెండాజిమ్",
    "Imidacloprid": "ఇమిడాక్లోప్రిడ్",
    "Mancozeb": "మ్యాంకోజెబ్",
    "Monocrotophos": "మోనోక్రోటోఫోస్",
}

# User session tracking
user_sessions = {}

# Language dictionary
responses = {
    "en": {
        "greeting": "👋 Hello farmer! Reply with your language: \n1⃣ English \n2⃣ తెలుగు",
        "ask_crop": "🌱 Enter your crop name:",
        "ask_category": "🗂 Select a pesticide category (reply with number):",
        "ask_pesticide1": "📌 Select a pesticide (reply with number):",
        "ask_pesticide2": "📌 Select another pesticide (reply with number):",
        "compatibility": "🧪 {} and {} are *{}*. ✅\n\n⚠️ *Precautions:*\n"
                         "1️⃣ Read Labels – Always check pesticide labels for compatibility instructions.\n"
                         "2️⃣ Perform a Jar Test – Mix small amounts in a container to check for separation or reactions.\n"
                         "3️⃣ Follow Mixing Order (WALES) – Wettable powders first, then liquids, then emulsifiables.",
        "no_data": "⚠️ No compatibility data found for this combination.",
        "restart": "🔄 Type *restart* to check another combination.",
    },
    "te": {
        "greeting": "👋 హలో రైతు! మీ భాషను ఎంచుకోండి: \n1⃣ English \n2⃣ తెలుగు",
        "ask_crop": "🌱 మీ పంట పేరు ఇవ్వండి:",
        "ask_category": "🗂 పెస్టిసైడ్ వర్గాన్ని ఎంచుకోండి (సంఖ్యతో ప్రత్యుత్తరం ఇవ్వండి):",
        "ask_pesticide1": "📌 ఒక పెస్టిసైడ్ ఎంచుకోండి (సంఖ్యతో ప్రత్యుత్తరం ఇవ్వండి):",
        "ask_pesticide2": "📌 మరొక పెస్టిసైడ్ ఎంచుకోండి (సంఖ్యతో ప్రత్యుత్తరం ఇవ్వండి):",
        "compatibility": "🧪 {} మరియు {} *{}* గా ఉన్నాయి. ✅\n\n⚠️ *జాగ్రత్తలు:*\n"
                         "1️⃣ లేబుళ్లు చదవండి – పొరపాట్లు లేకుండా పెస్టిసైడ్ లేబుళ్లను పరిశీలించండి.\n"
                         "2️⃣ జార్ టెస్ట్ చేయండి – చిన్న పరిమాణాలను కలిపి విభజన లేదా ప్రతిచర్యలు ఉన్నాయా చూడండి.\n"
                         "3️⃣ కలయిక క్రమాన్ని అనుసరించండి (WALES) – ముందుగా వెటిబుల్ పౌడర్లు, తరువాత లిక్విడ్లు, చివరగా ఎమల్సిఫైయబుల్స్.",
        "no_data": "⚠️ ఈ కలయిక కోసం డేటా లేదు.",
        "restart": "🔄 మరోసారి ప్రయత్నించేందుకు *restart* టైప్ చేయండి.",
    }
}

@app.route("/")
def home():
    return "Pesticide Chatbot is Running!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    if sender not in user_sessions or incoming_msg.lower() == "restart":
        user_sessions[sender] = {"step": "language"}

    session = user_sessions[sender]
    resp = MessagingResponse()
    msg = resp.message()

    if session["step"] == "language":
        if incoming_msg in ["1", "2"]:
            session["lang"] = "en" if incoming_msg == "1" else "te"
            session["step"] = "crop"
            msg.body(responses[session["lang"]]["ask_crop"])
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
                pesticides = df.iloc[:, 1].dropna().unique().tolist()
                
                session["pesticides1"] = pesticides
                display_names = [pesticide_translation.get(p, p) for p in pesticides] if session["lang"] == "te" else pesticides
                
                msg.body(responses[session["lang"]]["ask_pesticide1"] + "\n" + 
                         "\n".join([f"{i+1}. {p}" for i, p in enumerate(display_names)]))
            else:
                msg.body(responses[session["lang"]]["ask_category"])
        except ValueError:
            msg.body(responses[session["lang"]]["ask_category"])

    elif session["step"] == "pesticide1":
        try:
            index = int(incoming_msg) - 1
            session["pesticide1"] = session["pesticides1"][index]
            session["step"] = "pesticide2"
            df = data_sheets[session["selected_sheet"]]
            pesticides = df.iloc[:, 2].dropna().unique().tolist()
            
            session["pesticides2"] = pesticides
            display_names = [pesticide_translation.get(p, p) for p in pesticides] if session["lang"] == "te" else pesticides

            msg.body(responses[session["lang"]]["ask_pesticide2"] + "\n" + 
                     "\n".join([f"{i+1}. {p}" for i, p in enumerate(display_names)]))
        except:
            msg.body(responses[session["lang"]]["ask_pesticide1"])

    elif session["step"] == "pesticide2":
        try:
            index = int(incoming_msg) - 1
            session["pesticide2"] = session["pesticides2"][index]
            session["step"] = "restart"
            df = data_sheets[session["selected_sheet"]]
            match = df[(df.iloc[:, 1] == session["pesticide1"]) & 
                       (df.iloc[:, 2] == session["pesticide2"])]

            p1_display = pesticide_translation.get(session["pesticide1"], session["pesticide1"])
            p2_display = pesticide_translation.get(session["pesticide2"], session["pesticide2"])

            if not match.empty:
                compatibility = match.iloc[0, 3]
                msg.body(responses[session["lang"]]["compatibility"].format(p1_display, p2_display, compatibility))
            else:
                msg.body(responses[session["lang"]]["no_data"])

            msg.body(responses[session["lang"]]["restart"])
        except:
            msg.body(responses[session["lang"]]["ask_pesticide2"])

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
