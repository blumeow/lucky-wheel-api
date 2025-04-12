
from flask import Flask, request, jsonify, send_from_directory
from solana.rpc.api import Client
from solders.pubkey import Pubkey
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
    wallet_str = data.get("wallet")

    if not wallet_str:
        return jsonify({"eligible": False, "message": "No wallet provided"}), 400

    try:
        user_wallet = Pubkey.from_string(wallet_str)
    except Exception as e:
        return jsonify({"eligible": False, "message": f"Invalid wallet format: {str(e)}"}), 400

    try:
        txs = solana.get_signatures_for_address(user_wallet, limit=50)["result"]
    except Exception as e:
        return jsonify({"eligible": False, "message": f"Blockchain error: {str(e)}"}), 500

    try:
        for tx in txs:
            sig = tx["signature"]
            tx_detail = solana.get_transaction(sig, encoding="jsonParsed")["result"]
            if not tx_detail:
                continue
            instructions = tx_detail["transaction"]["message"]["instructions"]
            for instr in instructions:
                if "parsed" in instr and instr["program"] == "spl-token":
                    info = instr["parsed"]["info"]
                    if (
                        info.get("source") == wallet_str and
                        info.get("destination") == BURNER_ADDRESS and
                        info.get("mint") == BLU_TOKEN_MINT and
                        int(info.get("amount", 0)) >= REQUIRED_AMOUNT
                    ):
                        return jsonify({"eligible": True})
    except Exception as e:
        return jsonify({"eligible": False, "message": f"Parsing error: {str(e)}"}), 500

    return jsonify({"eligible": False, "message": "No valid BLU transaction found"})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
