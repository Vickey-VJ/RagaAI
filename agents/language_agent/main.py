from fastapi import FastAPI, Body
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

@app.post("/generate")
def generate_brief(inputs: dict = Body(...)):
    prompt = f"Create a market brief using: {inputs}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"brief": response.choices[0].message.content}
