
from flask import Flask, request, jsonify, send_from_directory
from solana.rpc.api import Client
from flask_cors import CORS
import os

app = Flask(__name__, static_folder="static")
CORS(app)
solana = Client("https://api.mainnet-beta.solana.com")

BURNER_ADDRESS = "EH1UKhLL9MTny9sCCGGrzVrbBAVAL6V3XsBXZvQ4wfe8"
BLU_TOKEN_MINT = "EWJZQLXkTfEzXxC3LgzZgTJiH6pY82xtLYnc3i5U2ZRV"
REQUIRED_AMOUNT = 2_000_000

@app.route("/api/check", methods=["POST"])
def check_wallet():
    data = request.get_json()
    user_wallet = data.get("wallet")

    if not user_wallet:
        return jsonify({"eligible": False, "message": "Wallet not provided."}), 400

    txs = solana.get_signatures_for_address(user_wallet, limit=100)["result"]

    for tx in txs:
        sig = tx["signature"]
        tx_detail = solana.get_transaction(sig, encoding="jsonParsed")["result"]

        if not tx_detail:
            continue

        instructions = tx_detail["transaction"]["message"]["instructions"]
        for instr in instructions:
            if "parsed" in instr and instr["program"] == "spl-token":
                info = instr["parsed"]["info"]
                if (info.get("source") == user_wallet and
                    info.get("destination") == BURNER_ADDRESS and
                    info.get("mint") == BLU_TOKEN_MINT and
                    int(info.get("amount", 0)) >= REQUIRED_AMOUNT):
                    return jsonify({"eligible": True})

    return jsonify({"eligible": False})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)
