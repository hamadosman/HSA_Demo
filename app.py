import os
import json
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.urandom(24)  # needed for flash messages

DATA_FILE = "database.json"

# ---------- Data Layer ----------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []

accounts = load_data()

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

# ---------- Business Logic ----------
ALLOWED_EXPENSES = {"doctor", "prescription", "dental", "vision", "therapy", "lab"}

def get_account(aid: int):
    for a in accounts:
        if a["id"] == aid:
            return a
    return None

def get_account_by_email(email: str):
    e = email.strip().lower()
    for a in accounts:
        if a.get("email", "").strip().lower() == e:
            return a
    return None

def create_an_account(name: str, email: str):
    n = name.strip()
    e = email.strip().lower()
    # prevent duplicate emails
    if get_account_by_email(e):
        return None
    new_id = len(accounts) + 1
    new_account = {
        "name": n,
        "email": e,
        "id": new_id,
        "balance": 0.0,
        "card_number": None,
        "transactions": [],
    }
    accounts.append(new_account)
    save_data()
    return new_account

def deposit_funds(account_id: int, amount: float):
    acct = get_account(account_id)
    if not acct:
        return None
    acct["balance"] += amount
    save_data()
    return acct

def issue_card(account_id: int):
    acct = get_account(account_id)
    if not acct:
        return None
    if not acct.get("card_number"):
        acct["card_number"] = f"4000-0000-0000-{account_id:04d}"
        save_data()
    return acct

def validate_transaction(account_id: int, amount: float, etype: str):
    acct = get_account(account_id)
    if not acct:
        return "denied"

    txn = {
        "type": etype,
        "amount": amount,
        "status": None,
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    if etype.strip().lower() not in ALLOWED_EXPENSES:
        txn["status"] = "denied"
        acct["transactions"].append(txn)
        save_data()
        return "denied"

    if amount > acct["balance"]:
        txn["status"] = "denied"
        acct["transactions"].append(txn)
        save_data()
        return "denied"

    txn["status"] = "approved"
    acct["transactions"].append(txn)
    acct["balance"] -= amount
    save_data()
    return "approved"

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/open_account", methods=["POST"])
def open_account_route():
    email = request.form.get("email", "").strip()
    acct = get_account_by_email(email)
    if not acct:
        flash(f'⚠️ Account with email "{email}" not found.')
        return redirect(url_for("home"))
    return redirect(url_for("account_page", account_id=acct["id"]))

@app.route("/create_account", methods=["POST"])
def create_account_route():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if not name or not email:
        flash("⚠️ Name and email are required.")
        return redirect(url_for("home"))
    acct = create_an_account(name, email)
    if acct:
        flash(f'✅ Account created! {acct["name"]} ({acct["email"]}) — ID #{acct["id"]}')
        return redirect(url_for("account_page", account_id=acct["id"]))
    else:
        flash(f'⚠️ An account with email "{email}" already exists. Please open it instead.')
        return redirect(url_for("home"))

@app.route("/account/<int:account_id>", methods=["GET"])
def account_page(account_id):
    acct = get_account(account_id)
    if not acct:
        flash("⚠️ Account not found.")
        return redirect(url_for("home"))
    return render_template("account.html", account=acct, allowed=sorted(ALLOWED_EXPENSES))

@app.route("/deposit", methods=["POST"])
def deposit_route():
    try:
        aid = int(request.form["account_id"])
        amount = float(request.form["amount"])
    except Exception:
        flash("⚠️ Invalid input.")
        return redirect(url_for("home"))
    res = deposit_funds(aid, amount)
    flash(f'💸 Deposited ${amount:.2f}' if res else "⚠️ Account not found.")
    return redirect(url_for("account_page", account_id=aid))

@app.route("/issue_card", methods=["POST"])
def issue_card_route():
    try:
        aid = int(request.form["account_id"])
    except Exception:
        flash("⚠️ Invalid account id.")
        return redirect(url_for("home"))
    res = issue_card(aid)
    flash(f'💳 Card: {res["card_number"]}' if res else "⚠️ Account not found.")
    return redirect(url_for("account_page", account_id=aid))

@app.route("/transaction", methods=["POST"])
def transaction_route():
    try:
        aid = int(request.form["account_id"])
        amount = float(request.form["amount"])
        etype = request.form["etype"]
    except Exception:
        flash("⚠️ Invalid input.")
        return redirect(url_for("home"))
    result = validate_transaction(aid, amount, etype)
    emoji = "✅" if result == "approved" else "❌"
    flash(f'{emoji} {result}: ${amount:.2f} ({etype})')
    return redirect(url_for("account_page", account_id=aid))

if __name__ == "__main__":
    app.run(debug=True)
