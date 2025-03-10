import mysql.connector
from cryptography.fernet import Fernet
import statistics

# Database connection class
class Database:
    def __init__(self):
        # Establish database connection
        self.conn = mysql.connector.connect(
            host="localhost", user="root", password="", database="financial_lending"
        )
        self.cursor = self.conn.cursor()
    
    def execute(self, query, values=None):
        # Execute queries with optional values
        self.cursor.execute(query, values) if values else self.cursor.execute(query)
        self.conn.commit()
        return self.cursor
    
    def fetchall(self):
        # Fetch all results
        return self.cursor.fetchall()

# Encryption utility class
class Encryption:
    key = Fernet.generate_key()
    cipher = Fernet(key)

    @staticmethod
    def encrypt(data):
        # Encrypt data
        return Encryption.cipher.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt(data):
        # Decrypt data
        return Encryption.cipher.decrypt(data.encode()).decode()

# Lender management class
class Lender:
    def __init__(self, db):
        self.db = db

    def add_lender(self, lender_id, name, balance, interest_rates):
        # Add a lender to the database
        encrypted_name = Encryption.encrypt(name)
        query = "INSERT INTO lenders (lender_id, name, balance, interest_rates) VALUES (%s, %s, %s, %s)"
        self.db.execute(query, (lender_id, encrypted_name, balance, interest_rates))

    def get_lenders(self):
        # Retrieve all lenders from the database
        query = "SELECT lender_id, interest_rates, balance FROM lenders"
        self.db.execute(query)
        return self.db.fetchall()

# Borrower management class
class Borrower:
    def __init__(self, db):
        self.db = db

    def add_borrower(self, borrower_id, name, credit_rating, preferred_rates):
        # Add a borrower to the database
        encrypted_name = Encryption.encrypt(name)
        query = "INSERT INTO borrowers (borrower_id, name, credit_rating, preferred_interest_rates) VALUES (%s, %s, %s, %s)"
        self.db.execute(query, (borrower_id, encrypted_name, credit_rating, preferred_rates))

    def get_borrower_rates(self, borrower_id):
        # Retrieve preferred interest rates for a borrower
        query = "SELECT preferred_interest_rates FROM borrowers WHERE borrower_id=%s"
        self.db.execute(query, (borrower_id,))
        result = self.db.fetchall()
        return [int(rate) for rate in result[0][0].split(',')] if result else []

# Loan management class
class Loan:
    def __init__(self, db):
        self.db = db

    def match_interest_rates(self, lender_rates, borrower_rates):
        # Sort lender and borrower interest rates
        lender_rates.sort()
        borrower_rates.sort(reverse=True)
        print("Sorted Lender Interest Rates (Ascending):", lender_rates)
        print("Sorted Borrower Interest Rates (Descending):", borrower_rates)
        
        # Find matching interest rate
        for lender_rate in lender_rates:
            for borrower_rate in borrower_rates:
                if lender_rate <= borrower_rate:
                    # If rates are close, take the average
                    if abs(lender_rate - borrower_rate) <= 1:
                        return round(statistics.mean([lender_rate, borrower_rate]), 2)
                    else:
                        return lender_rate
        return None

    def create_loan(self, borrower_id, amount, tenure, lender_obj, borrower_obj):
        # Create a loan agreement
        borrower_rates = borrower_obj.get_borrower_rates(borrower_id)
        lenders = lender_obj.get_lenders()
        matched_lenders = []
        matched_rate = None
        total_funds = 0
        
        # Match borrower with lenders
        for lender in lenders:
            lender_id, lender_rates, balance = lender
            lender_rates = [int(rate) for rate in lender_rates.split(',')]
            rate = self.match_interest_rates(lender_rates, borrower_rates)
            if rate and balance >= amount:
                matched_lenders.append((lender_id, rate, balance))
                matched_rate = rate
                total_funds += balance
                if total_funds >= amount:
                    break
        
        # Insert loan record if sufficient funds are found
        if matched_lenders and total_funds >= amount:
            loan_id = f"LN{borrower_id}"
            query = "INSERT INTO loans (loan_id, borrower_id, lender_id, amount, tenure, interest_rate, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            for lender_id, rate, balance in matched_lenders:
                self.db.execute(query, (loan_id, borrower_id, lender_id, amount, tenure, matched_rate, "active"))
                self.db.execute("UPDATE lenders SET balance=%s WHERE lender_id=%s", (balance - amount, lender_id))
            return "Loan Agreement Created Successfully"
        else:
            return "No suitable lender found"

# Main execution
if __name__ == "__main__":
    db = Database()
    lender_obj = Lender(db)
    borrower_obj = Borrower(db)
    loan_obj = Loan(db)
    
    # Adding sample lender and borrower
    lender_obj.add_lender(10001, "John Doe", 5000, "5,7,10")
    borrower_obj.add_borrower(1, "Jane Smith", "Good", "6,8")
    
    # Creating a loan
    print(loan_obj.create_loan(1, 3000, 12, lender_obj, borrower_obj))

