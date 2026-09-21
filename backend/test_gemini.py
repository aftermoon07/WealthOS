import httpx
import json
import asyncio

async def test():
    models = ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-lite-latest", "gemini-pro-latest"]
    
    for model in models:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=YOUR_API_KEY"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": "Return { 'a': 1 }"}]}],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url, json=payload)
            data = resp.json()
            if 'error' in data:
                print(f"{model}: {data['error'].get('code')} - {data['error'].get('message')}")
            else:
                print(f"{model}: SUCCESS")
                return

asyncio.run(test())
