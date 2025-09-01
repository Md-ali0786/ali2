from flask import Flask, render_template, request, jsonify, session
import requests
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change for production

# Your 2Factor API key (rotate it if it was exposed; prefer environment variable)
TWOFACTOR_API_KEY = os.getenv("TWOFACTOR_API_KEY", "5f560908-7f29-11f0-a562-0200cd936042")
OTP_TEMPLATE_NAME = "project"  # EXACT name from 2Factor SMS OTP template

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/send_otp", methods=["POST"])
def send_otp():
    mobile = request.form.get("mobile", "").strip()

    if not TWOFACTOR_API_KEY or TWOFACTOR_API_KEY == "REPLACE_WITH_REAL_KEY":
        return jsonify({"status": "failed", "error": "API key not configured"}), 500
    if not mobile:
        return jsonify({"status": "failed", "error": "mobile is required"}), 400

    try:
        # OTP AUTOGEN WITH TEMPLATE (forces use of your approved SMS OTP template)
        # Syntax per 2Factor KB:
        # https://2factor.in/API/V1/{api_key}/SMS/{phone_number}/AUTOGEN/{template_name}
        url = f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/{mobile}/AUTOGEN/{OTP_TEMPLATE_NAME}"
        resp = requests.get(url, timeout=15)

        # Log provider response while debugging
        print("2Factor OTP:", resp.status_code, resp.text)

        # Expect JSON: {"Status":"Success","Details":"<session_id>"} OR {"Status":"Error","Details":"..."}
        result = resp.json()
        if result.get("Status") == "Success":
            session["session_id"] = result.get("Details")
            return jsonify({"status": "sent"})
        else:
            return jsonify({"status": "failed", "error": result.get("Details")}), 400

    except requests.exceptions.RequestException as re:
        return jsonify({"status": "failed", "error": f"Network error: {str(re)}"}), 502
    except ValueError:
        return jsonify({"status": "failed", "error": f"Non-JSON response from provider: {resp.text[:200]}"}), 502
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    user_otp = request.form.get("otp", "").strip()
    session_id = session.get("session_id")

    if not user_otp:
        return jsonify({"status": "failed", "error": "otp is required"}), 400
    if not session_id:
        return jsonify({"status": "failed", "error": "No OTP session. Please request OTP again."}), 400

    try:
        # OTP VERIFY endpoint
        # https://2factor.in/API/V1/{api_key}/SMS/VERIFY/{session_id}/{otp}
        url = f"https://2factor.in/API/V1/{TWOFACTOR_API_KEY}/SMS/VERIFY/{session_id}/{user_otp}"
        resp = requests.get(url, timeout=15)
        print("2Factor VERIFY:", resp.status_code, resp.text)

        result = resp.json()
        if result.get("Status") == "Success":
            # Clear on success
            session.pop("session_id", None)
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "failed", "error": result.get("Details")}), 400

    except requests.exceptions.RequestException as re:
        return jsonify({"status": "failed", "error": f"Network error: {str(re)}"}), 502
    except ValueError:
        return jsonify({"status": "failed", "error": f"Non-JSON response from provider: {resp.text[:200]}"}), 502
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

if __name__ == "__main__":
    print("API key configured:", bool(TWOFACTOR_API_KEY and TWOFACTOR_API_KEY != "REPLACE_WITH_REAL_KEY"))
    app.run(debug=True)
