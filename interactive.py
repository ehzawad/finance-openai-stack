import asyncio
import aiohttp
import uuid
from typing import Optional
import sys
import os

class BankingBotClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.session_id: Optional[str] = None
        
    async def start_session(self):
        """Start a new chat session"""
        self.session_id = str(uuid.uuid4())
        
    async def end_session(self):
        """End the current chat session"""
        if self.session_id:
            async with aiohttp.ClientSession() as session:
                async with session.delete(f"{self.server_url}/chat/{self.session_id}") as response:
                    if response.status == 200:
                        self.session_id = None
                        return True
        return False

    async def send_message(self, message: str) -> str:
        """Send a message to the bot and get the response"""
        if not self.session_id:
            raise ValueError("No active session")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/chat/{self.session_id}",
                json={"message": message}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["response"]
                else:
                    return f"Error: {response.status}"

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    async def run_interactive(self):
        """Run the interactive chat session"""
        self.clear_screen()
        await self.start_session()
        
        print("=== Banking Assistant Interactive Client ===")
        print("Type 'quit' to exit\n")
        print("Assistant: How can I help you today?")

        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()
                
                # Check for quit command
                if user_input.lower() == 'quit':
                    print("\nAssistant: Thank you for using our banking service. Goodbye!")
                    await self.end_session()
                    break

                # Send message and get response
                response = await self.send_message(user_input)
                print(f"\nAssistant: {response}")

            except KeyboardInterrupt:
                print("\n\nExiting gracefully...")
                await self.end_session()
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again.")

async def main():
    client = BankingBotClient()
    await client.run_interactive()

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
