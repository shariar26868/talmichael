import asyncio
import json
from openai import AsyncOpenAI
from app.core.config import settings

async def test_translation():
    if not settings.openai_api_key:
        print("OpenAI API key not set")
        return
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    hebrew_names = ["בנימין נתניהו", "יאיר לפיד", "בצלאל סמוטריץ'", "אריה דרעי", "מירי רגב", "איתמר בן גביר"]
    
    prompt = f"""
    Translate this list of Hebrew names of Israeli politicians into standard English transliterated names:
    {hebrew_names}
    
    Respond only with a JSON object mapping the Hebrew name to the English name. E.g.:
    {{"בנימין נתניהו": "Benjamin Netanyahu"}}
    """
    
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    result = json.loads(resp.choices[0].message.content)
    print("Translation result:")
    print(json.dumps(result, indent=2))

asyncio.run(test_translation())
