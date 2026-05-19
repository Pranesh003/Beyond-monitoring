import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(dotenv_path="c:\\Users\\prane\\OneDrive\\Desktop\\abb acle\\backend\\.env")

key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=key)

models_to_test = [
    'gemini-2.5-flash',
    'gemini-flash-latest',
    'gemini-pro-latest',
    'gemini-2.0-flash'
]

for m_name in models_to_test:
    print(f"\n--- Testing model: {m_name} ---")
    try:
        model = genai.GenerativeModel(m_name)
        response = model.generate_content("Hello! Confirm you can hear me in 1 sentence.")
        print(f"SUCCESS with {m_name}:")
        print(response.text)
        break
    except Exception as e:
        print(f"FAILED with {m_name}: {str(e)[:250]}")
