from openai import AsyncOpenAI
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mock_data_loader import MockDataLoader

class UserInput(BaseModel):
    message: str

class AsyncBankingChatbot:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.mock_data = MockDataLoader()
        
        # Store conversations by session ID
        self.conversations: Dict[str, List[Dict[str, str]]] = {}

    def get_initial_conversation(self) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """You are a banking assistant that helps users check their account information. If an user speaks in Bengali, you reply in Bengali. Always reply in Bengali, but never use emojis. And Be concise and succinct.
                Follow a strict flow:
                1. Ask for account number first
                2. Then ask for PIN
                3. Then provide detailed account information including:
                   - Current balance with currency symbol
                   - Account type and its features
                   - Account status
                   - Last transaction date
                   - Account holder name
                
                Be professional but friendly. Use the provided functions to validate all information.
                If an account is frozen, warn the user appropriately."""
            }
        ]

    def validate_account_number(self, account_number: str) -> Dict[str, Any]:
        account = self.mock_data.get_account(account_number)
        is_valid = bool(account)
        return {
            "valid": is_valid,
            "message": "Account found" if is_valid else "Account not found",
            "account_status": account.get("account_status") if is_valid else None
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
        
        # Get account type details
        account_type_details = self.mock_data.get_account_type_details(account["account_type"])
        
        return {
            "status": "success",
            "data": {
                "balance": account["balance"],
                "currency": account["currency"],
                "account_type": account["account_type"],
                "formatted_balance": self.mock_data.get_formatted_balance(account_number),
                "account_holder": account["account_holder"],
                "account_status": account["account_status"],
                "last_transaction": account["last_transaction"],
                "account_features": {
                    "daily_withdrawal_limit": account_type_details.get("daily_withdrawal_limit"),
                    "minimum_balance": account_type_details.get("minimum_balance"),
                    "interest_rate": account_type_details.get("interest_rate"),
                    "monthly_fee": account_type_details.get("monthly_fee"),
                    "term_length": account_type_details.get("term_length")
                }
            }
        }

    async def process_message(self, session_id: str, user_input: str) -> str:
        # Initialize conversation history if it doesn't exist
        if session_id not in self.conversations:
            self.conversations[session_id] = self.get_initial_conversation()
        
        # Add user message to history
        self.conversations[session_id].append({"role": "user", "content": user_input})

        # Get completion from OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=self.conversations[session_id],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "validate_account_number",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "account_number": {"type": "string"}
                            },
                            "required": ["account_number"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "validate_pin",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "account_number": {"type": "string"},
                                "pin": {"type": "string"}
                            },
                            "required": ["account_number", "pin"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_account_balance",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "account_number": {"type": "string"},
                                "pin": {"type": "string"}
                            },
                            "required": ["account_number", "pin"]
                        }
                    }
                }
            ],
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        
        # Handle any function calls
        if assistant_message.tool_calls:
            # Process each function call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Call the appropriate function
                if function_name == "validate_account_number":
                    function_response = self.validate_account_number(function_args["account_number"])
                elif function_name == "validate_pin":
                    function_response = self.validate_pin(
                        function_args["account_number"],
                        function_args["pin"]
                    )
                elif function_name == "get_account_balance":
                    function_response = self.get_account_balance(
                        function_args["account_number"],
                        function_args["pin"]
                    )
                
                # Append the function call and result to the conversation
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                })
                self.conversations[session_id].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_response)
                })
            
            # Get the final response after function calls
            second_response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=self.conversations[session_id]
            )
            assistant_response = second_response.choices[0].message.content
        else:
            assistant_response = assistant_message.content

        # Add assistant's response to history
        self.conversations[session_id].append({"role": "assistant", "content": assistant_response})
        
        return assistant_response

# Create FastAPI app and chatbot instance
app = FastAPI()
chatbot = AsyncBankingChatbot()

@app.post("/chat/{session_id}")
async def chat_endpoint(session_id: str, user_input: UserInput):
    try:
        response = await chatbot.process_message(session_id, user_input.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{session_id}")
async def end_session(session_id: str):
    if session_id in chatbot.conversations:
        del chatbot.conversations[session_id]
    return {"message": "Session ended successfully"}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
