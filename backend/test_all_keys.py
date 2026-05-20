import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

primary_key = os.getenv("GEMINI_API_KEY")
backup_keys_str = os.getenv("GEMINI_BACKUP_KEYS", "")
backup_keys = [k.strip() for k in backup_keys_str.split(",") if k.strip()]

all_keys = []
if primary_key:
    all_keys.append(primary_key)
for bk in backup_keys:
    if bk not in all_keys:
        all_keys.append(bk)

print(f"Testing a total of {len(all_keys)} keys...")

for idx, key in enumerate(all_keys):
    masked = f"...{key[-6:]}" if len(key) >= 6 else "invalid"
    print(f"\n--- Testing Key {idx + 1}/{len(all_keys)} ending with: {masked} ---")
    try:
        genai.configure(api_key=key)
        # We can try different models
        for m_name in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content("Hello! Confirm you can hear me in 1 sentence.")
                print(f"  SUCCESS with model {m_name}: {response.text.strip()}")
                break
            except Exception as e:
                print(f"  FAILED with model {m_name}: {str(e)[:200]}")
    except Exception as e:
        print(f"  Configuration failed: {e}")
