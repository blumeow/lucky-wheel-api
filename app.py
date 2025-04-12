
from flask import Flask, request, jsonify, send_from_directory
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.signature import Signature
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
        resp = solana.get_signatures_for_address(user_wallet, limit=50)
        txs = resp.value
    except Exception as e:
        return jsonify({"eligible": False, "message": f"Blockchain error: {str(e)}"}), 500

    try:
        for tx in txs:
            sig_obj = Signature.from_string(str(tx.signature))
            tx_resp = solana.get_transaction(sig_obj, encoding="jsonParsed")
            tx_detail = tx_resp.value
            if tx_detail is None:
                continue

            tx_json = tx_detail.to_json()
            inner_instructions = tx_json.get("meta", {}).get("innerInstructions", [])

            for inner in inner_instructions:
                for instr in inner.get("instructions", []):
                    if isinstance(instr, dict):
                        parsed = instr.get("parsed", {})
                        if parsed.get("type") == "transfer":
                            info = parsed.get("info", {})
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
