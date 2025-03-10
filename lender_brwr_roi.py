import mysql.connector
from cryptography.fernet import Fernet
import math

# Generate encryption key (Store this securely for future decryption)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Database connection setup
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="new_password",
        database="financial_lending1"
    )

# Create Database and Tables
def setup_database():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="new_password"
    )
    cursor = db.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS financial_lending")
    db.close()
    
    db = connect_db()
    cursor = db.cursor()
    
    # Creating tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lenders_tbl (
        lender_id INT PRIMARY KEY CHECK (lender_id BETWEEN 10001 AND 20000),
        name VARCHAR(255),
        encrypted_details TEXT,
        balance DECIMAL(10,2) DEFAULT 0.00,
        interest_rate FLOAT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS borrowers_tbl (
        borrower_id INT PRIMARY KEY CHECK (borrower_id BETWEEN 1 AND 10000),
        name VARCHAR(255),
        credit_rating FLOAT,
        encrypted_details TEXT,
        preferred_interest_rates TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loans_tbl (
        loan_id INT AUTO_INCREMENT PRIMARY KEY,
        borrower_id INT,
        amount DECIMAL(10,2),
        interest_rate FLOAT,
        tenure INT,
        emi DECIMAL(10,2),
        remaining_balance DECIMAL(10,2),
        FOREIGN KEY (borrower_id) REFERENCES borrowers_tbl(borrower_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS loan_lenders (
        loan_id INT,
        lender_id INT,
        contribution DECIMAL(10,2),
        FOREIGN KEY (loan_id) REFERENCES loans_tbl(loan_id),
        FOREIGN KEY (lender_id) REFERENCES lenders_tbl(lender_id)
    )
    """)
    
    db.commit()
    db.close()

# Encrypt and store data
def encrypt_data(data):
    return cipher_suite.encrypt(data.encode()).decode()

# Decrypt data
def decrypt_data(encrypted_data):
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

# Lender Onboarding
def add_lender(lender_id, name, details, balance, interest_rate):
    db = connect_db()
    cursor = db.cursor()
    encrypted_details = encrypt_data(details)
    cursor.execute("INSERT INTO lenders_tbl (lender_id, name, encrypted_details, balance, interest_rate) VALUES (%s, %s, %s, %s, %s)", 
                   (lender_id, name, encrypted_details, balance, interest_rate))
    db.commit()
    db.close()

# Borrower Onboarding
def add_borrower(borrower_id, name, credit_rating, details, preferred_interest_rates):
    db = connect_db()
    cursor = db.cursor()
    encrypted_details = encrypt_data(details)
    cursor.execute("INSERT INTO borrowers_tbl (borrower_id, name, credit_rating, encrypted_details, preferred_interest_rates) VALUES (%s, %s, %s, %s, %s)", 
                   (borrower_id, name, credit_rating, encrypted_details, preferred_interest_rates))
    db.commit()
    db.close()

# Sort and Match Interest Rates
def sort_and_match_interest_rates(borrower_interest_rates, lender_interest_rates):
    borrower_interest_rates.sort()
    lender_interest_rates.sort()
    print("Sorted Borrower Interest Rates:", borrower_interest_rates)
    print("Sorted Lender Interest Rates:", lender_interest_rates)
    
    for rate in borrower_interest_rates:
        if rate in lender_interest_rates:
            return rate
    return None

# Loan Agreement with Matching Interest Rate
def create_loan(borrower_id, amount, tenure):
    db = connect_db()
    cursor = db.cursor()
    
    # Get borrower interest preferences
    cursor.execute("SELECT preferred_interest_rates FROM borrowers_tbl WHERE borrower_id = %s", (borrower_id,))
    borrower_interest_rates = cursor.fetchone()
    
    if borrower_interest_rates is None:
        print("\nBorrower not found.")
        db.close()
        return
    
    borrower_interest_rates = list(map(float, borrower_interest_rates[0].split(',')))
    
    # Get unique lender interest rates
    cursor.execute("SELECT DISTINCT interest_rate FROM lenders_tbl WHERE balance > 0")
    lender_interest_rates = [row[0] for row in cursor.fetchall()]
    
    # Sort and match interest rates
    matching_rate = sort_and_match_interest_rates(borrower_interest_rates, lender_interest_rates)
    
    if matching_rate is None:
        print("\nNo matching interest rates found between lenders_tbl and borrower.")
        db.close()
        return
    
    # Collect funds from matching lenders_tbl
    cursor.execute("SELECT lender_id, balance FROM lenders_tbl WHERE balance > 0 AND interest_rate = %s ORDER BY balance DESC", 
                   (matching_rate,))
    lenders_tbl = cursor.fetchall()
    
    total_funded = 0
    lender_contributions = []
    for lender_id, balance in lenders_tbl:
        contribution = min(balance, amount - total_funded)
        lender_contributions.append((lender_id, contribution))
        total_funded += contribution
        if total_funded >= amount:
            break
    
    if total_funded < amount:
        print("\n Not enough funds available from matching lenders_tbl.")
        db.close()
        return
    
    # Calculate EMI
    r = (matching_rate / 100) / 12
    n = tenure
    emi = (amount * r * math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1)
    
    # Create loan agreement
    cursor.execute("INSERT INTO loans_tbl (borrower_id, amount, interest_rate, tenure, emi, remaining_balance) VALUES (%s, %s, %s, %s, %s, %s)",
                   (borrower_id, amount, matching_rate, tenure, emi, amount))
    loan_id = cursor.lastrowid
    
    for lender_id, contribution in lender_contributions:
        cursor.execute("INSERT INTO loan_lenders (loan_id, lender_id, contribution) VALUES (%s, %s, %s)",
                       (loan_id, lender_id, contribution))
        cursor.execute("UPDATE lenders_tbl SET balance = balance - %s WHERE lender_id = %s", (contribution, lender_id))
    
    cursor.execute("SELECT name FROM borrowers_tbl WHERE borrower_id = %s", (borrower_id,))
    name_br = cursor.fetchone()
    print("\nLoan agreement created successfully with matched interest rate.",name_br)
      
    db.commit()
    db.close()
    
# Loan Repayment
def loan_repayment(loan_id):
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT emi, remaining_balance FROM loans_tbl WHERE loan_id = %s", (loan_id,))
    loan_data = cursor.fetchone()
    
    if loan_data is None:
        print("\n")
        print("Loan not found.")
        db.close()
        return
    
    emi, remaining_balance = loan_data
    
    if remaining_balance <= 0:
        print("\n")
        print("Loan fully repaid.")
        db.close()
        return
    
    new_balance = remaining_balance - emi
    cursor.execute("UPDATE loans_tbl SET remaining_balance = %s WHERE loan_id = %s", (new_balance, loan_id))
    
    cursor.execute("SELECT lender_id, contribution FROM loan_lenders WHERE loan_id = %s", (loan_id,))
    lenders = cursor.fetchall()
    for lender_id, contribution in lenders:
        lender_payment = (contribution / remaining_balance) * emi
        cursor.execute("UPDATE lenders_tbl SET balance = balance + %s WHERE lender_id = %s", (lender_payment, lender_id))
    
    db.commit()
    db.close()
    print("\n")
    print(f"Loan ID {loan_id}: EMI of {emi:.2f} paid. Remaining Balance: {new_balance:.2f}")

    
# Initialize Database
setup_database()

if __name__ == "__main__":
    create_loan(4151, 6000, 1);
    create_loan(2516, 6000, 1);
    
    loan_repayment(17)
