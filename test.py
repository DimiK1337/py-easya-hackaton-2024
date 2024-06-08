from xrpl.account import get_balance
from xrpl.clients import JsonRpcClient
from xrpl.models import Payment, Memo
from xrpl.transaction import submit_and_wait
from xrpl.wallet import generate_faucet_wallet

# Read in a PDF file using Py2PDF
from PyPDF2 import PdfReader

def read_pdf(file):
    with open(file, "rb") as f:
        pdf = PdfReader(f)
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text



# Create a client to connect to the test network
XRP_CLIENT = "https://s.altnet.rippletest.net:51234"
client = JsonRpcClient(XRP_CLIENT)

# Create wallets for the sender and recipient
sender_wallet = generate_faucet_wallet(client, debug=True)
recipient_wallet = generate_faucet_wallet(client, debug=True)

# Display initial balances
print("Initial Balances:")
print("Sender Wallet:", get_balance(sender_wallet.classic_address, client))
print("Recipient Wallet:", get_balance(recipient_wallet.classic_address, client))

def upload_credit_score(credit_score, sender_wallet, recipient_wallet):
    memo_data = f"Credit Score: {credit_score}"
    memo = Memo(memo_data=memo_data.encode('utf-8').hex())
    
    payment_tx = Payment(
        account=sender_wallet.classic_address,
        destination=recipient_wallet.classic_address,
        amount="1000",  # Amount in drops
        memos=[memo]
    )
    
    payment_response = submit_and_wait(payment_tx, client, sender_wallet)
    return payment_response

# Upload 3 credit scores
credit_scores = [read_pdf(f"./data/credit-score-{i}.pdf") for i in range(1, 4)]
responses = [upload_credit_score(score, sender_wallet, recipient_wallet) for score in credit_scores]

# Print responses and decrypted memos
for i, response in enumerate(responses):
    print(f"\nResponse for credit score {credit_scores[i]}:")
    print(response)
    for memo in response.result["Memos"]:
        memo_data_hex = memo["Memo"]["MemoData"]
        memo_data = bytes.fromhex(memo_data_hex).decode('utf-8')
        print(f"Decrypted memo: {memo_data}")

# Display final balances
print("\nFinal Balances:")
print("Sender Wallet:", get_balance(sender_wallet.classic_address, client))
print("Recipient Wallet:", get_balance(recipient_wallet.classic_address, client))


