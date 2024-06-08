from flask import request, jsonify, render_template
import os
import tempfile
from app import app
from xrpl.wallet import generate_faucet_wallet
from xrpl.clients import JsonRpcClient
from xrpl.transaction import send_reliable_submission
from xrpl.models.transactions import Payment, Memo
from xrpl.models.requests import AccountTx
from xrpl.utils import xrp_to_drops
from PyPDF2 import PdfFileReader

client = JsonRpcClient("https://s.altnet.rippletest.net:51234/")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_wallet', methods=['GET'])
def generate_wallet():
    wallet = generate_faucet_wallet(client)
    return jsonify({
        'address': wallet.classic_address,
        'seed': wallet.seed
    })

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files or 'wallet_address' not in request.form:
        return jsonify({'error': 'No file or wallet address provided'}), 400

    file = request.files['file']
    wallet_address = request.form['wallet_address']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.pdf'):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_file.name)
        credit_score = extract_credit_score(temp_file.name)
        os.remove(temp_file.name)
        if credit_score:
            mint_transaction(wallet_address, credit_score)
            return jsonify({'credit_score': credit_score}), 200
        else:
            return jsonify({'error': 'Credit score not found'}), 400
    else:
        return jsonify({'error': 'Invalid file type'}), 400

def extract_credit_score(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfFileReader(f)
            num_pages = reader.getNumPages()
            for page_num in range(num_pages):
                page = reader.getPage(page_num)
                text = page.extract_text()
                credit_score = find_credit_score_in_text(text)
                if credit_score:
                    return credit_score
        return None
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def find_credit_score_in_text(text):
    import re
    match = re.search(r'\b\d{3}\b', text)
    if match:
        return match.group(0)
    return None

def mint_transaction(wallet_address, credit_score):
    wallet = generate_faucet_wallet(client)  # Generate a new wallet to mint the transaction
    memo = Memo(
        memo_data=str(credit_score).encode('utf-8').hex()
    )
    payment = Payment(
        account=wallet.classic_address,
        amount=xrp_to_drops(10),  # Send 10 XRP
        destination=wallet_address,
        memos=[memo]
    )
    signed_tx = xrpl.transaction.safe_sign_transaction(payment, wallet)
    response = send_reliable_submission(signed_tx, client)
    print(f"Transaction result: {response.result['meta']['TransactionResult']}")
    print(f"Transaction hash: {signed_tx.get_hash()}")

@app.route('/get_credit_scores', methods=['GET'])
def get_credit_scores():
    wallet_address = request.args.get('wallet_address')
    if not wallet_address:
        return jsonify({'error': 'No wallet address provided'}), 400

    credit_scores = retrieve_credit_scores(wallet_address)
    return jsonify({'credit_scores': credit_scores}), 200

def retrieve_credit_scores(wallet_address):
    account_tx_request = AccountTx(account=wallet_address)
    response = client.request(account_tx_request)
    transactions = response.result['transactions']

    credit_scores = []
    for tx in transactions:
        if 'memos' in tx['tx']:
            for memo in tx['tx']['memos']:
                memo_data = bytes.fromhex(memo['memo']['memo_data']).decode('utf-8')
                if memo_data.isdigit():
                    credit_scores.append(memo_data)

    return credit_scores
