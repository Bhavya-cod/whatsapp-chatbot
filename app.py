from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Pesticide combination dataset (Sample)
PESTICIDE_COMBINATIONS = {
    "aphids": "Use Neem Oil + Pyrethrin",
    "fungus": "Use Copper Fungicide + Sulfur",
    "weeds": "Use Glyphosate + Diquat"
}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body").lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in PESTICIDE_COMBINATIONS:
        response_text = f"Recommended combination: {PESTICIDE_COMBINATIONS[incoming_msg]}"
    else:
        response_text = "Sorry, I don't have a recommendation for that. Please enter a valid pest or disease name."

    msg.body(response_text)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
