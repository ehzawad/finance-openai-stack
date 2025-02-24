import json
from typing import Dict, Any
from pathlib import Path

class MockDataLoader:
    def __init__(self, mock_data_path: str = "mock_accounts.json"):
        self.mock_data_path = Path(mock_data_path)
        self.data: Dict[str, Any] = {}
        self.load_data()
    
    def load_data(self) -> None:
        """Load mock data from JSON file"""
        try:
            with open(self.mock_data_path, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            print(f"Mock data file not found at {self.mock_data_path}")
            self.data = {"accounts": {}, "account_types": {}, "currencies": {}}
    
    def get_account(self, account_number: str) -> Dict[str, Any]:
        """Get account details by account number"""
        return self.data.get("accounts", {}).get(account_number, {})
    
    def get_account_type_details(self, account_type: str) -> Dict[str, Any]:
        """Get account type details"""
        return self.data.get("account_types", {}).get(account_type, {})
    
    def get_currency_details(self, currency_code: str) -> Dict[str, Any]:
        """Get currency details"""
        return self.data.get("currencies", {}).get(currency_code, {})
    
    def validate_account_and_pin(self, account_number: str, pin: str) -> bool:
        """Validate account number and PIN combination"""
        account = self.get_account(account_number)
        return account.get("pin") == pin

    def get_formatted_balance(self, account_number: str) -> str:
        """Get formatted balance with currency symbol"""
        account = self.get_account(account_number)
        if not account:
            return "Account not found"
        
        currency = self.get_currency_details(account.get("currency", "USD"))
        symbol = currency.get("symbol", "$")
        return f"{symbol}{account.get('balance', 0):,.2f}"

    def get_account_status(self, account_number: str) -> str:
        """Get account status"""
        account = self.get_account(account_number)
        return account.get("account_status", "unknown")

    @property
    def mock_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get all accounts data for compatibility with existing code"""
        return self.data.get("accounts", {})

# Example usage in AsyncBankingChatbot:
"""
class AsyncBankingChatbot:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.mock_data = MockDataLoader()
        
        # Use mock_data directly or for compatibility:
        self.mock_accounts = self.mock_data.mock_accounts
        
    def validate_account_number(self, account_number: str) -> Dict[str, Any]:
        return {
            "valid": account_number in self.mock_data.mock_accounts,
            "message": "Account found" if account_number in self.mock_data.mock_accounts else "Account not found"
        }

    def validate_pin(self, account_number: str, pin: str) -> Dict[str, Any]:
        is_valid = self.mock_data.validate_account_and_pin(account_number, pin)
        return {
            "valid": is_valid,
            "message": "PIN validated" if is_valid else "Invalid PIN"
        }

    def get_account_balance(self, account_number: str, pin: str) -> Dict[str, Any]:
        if not self.mock_data.validate_account_and_pin(account_number, pin):
            return {"status": "error", "message": "Invalid credentials"}
        
        account = self.mock_data.get_account(account_number)
        if not account:
            return {"status": "error", "message": "Account not found"}
        
        return {
            "status": "success",
            "data": {
                "balance": account["balance"],
                "currency": account["currency"],
                "account_type": account["account_type"],
                "formatted_balance": self.mock_data.get_formatted_balance(account_number),
                "account_holder": account["account_holder"],
                "account_status": account["account_status"],
                "last_transaction": account["last_transaction"]
            }
        }
"""
