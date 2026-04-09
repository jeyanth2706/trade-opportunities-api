import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"API Key: {api_key[:20]}...")

try:
    genai.configure(api_key=api_key)
    
    # Use the latest available model
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content("Say hello briefly")
    print(f"✅ Gemini works! Response: {response.text[:100]}")
except Exception as e:
    print(f"❌ Gemini error: {e}")