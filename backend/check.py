import google.generativeai as genai
import os

# PASTE YOUR KEY HERE
os.environ["GOOGLE_API_KEY"] = "AIzaSyD4EhNTOdE3-SDbtzQbmI692smRBzLziAI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print("🔍 Checking available models for this key...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ AVAILABLE: {m.name}")
except Exception as e:
    print(f"❌ Error: {e}")