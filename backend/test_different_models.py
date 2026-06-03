import os
import json
import logging
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

from database.queries import get_topics_for_paper
from pipeline.agents.agent_08_critic import _build_system_prompt, _build_user_message, _load_constitution

topics = get_topics_for_paper("2352203601")
topic = topics[0]

constitution = _load_constitution()
system_prompt = _build_system_prompt(constitution)
user_message = _build_user_message(topic, None, None)

models_to_test = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-latest", "gemini-pro-latest"]

for model_name in models_to_test:
    print(f"\n======================================")
    print(f"Testing model: {model_name}")
    print(f"======================================")
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
        )
        response = model.generate_content(user_message)
        print("Candidate finish reason:", response.candidates[0].finish_reason)
        print("Text generated length:", len(response.text))
        print("Generated text:\n", response.text)
    except Exception as e:
        print(f"Failed for {model_name}: {e}")
