import os
import json
import logging
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Load env vars
load_dotenv(Path(__file__).resolve().parent / ".env")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

from database.queries import get_topics_for_paper
from pipeline.agents.agent_08_critic import _build_system_prompt, _build_user_message, _load_constitution

# Fetch topics
topics = get_topics_for_paper("2352203601")
if not topics:
    print("No topics found for paper 2352203601!")
    exit(1)

topic = topics[0]
print(f"Topic: {topic.get('topic_name')}")

constitution = _load_constitution()
system_prompt = _build_system_prompt(constitution)
user_message = _build_user_message(topic, None, None)

print("System Prompt Length:", len(system_prompt))
print("User Message Length:", len(user_message))

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=system_prompt,
    generation_config=genai.types.GenerationConfig(
        max_output_tokens=2048,
        response_mime_type="application/json",
    )
)

print("\n--- Sending request to gemini-2.5-flash ---")
response = model.generate_content(user_message)

print("\n--- Response candidates ---")
for idx, candidate in enumerate(response.candidates):
    print(f"Candidate {idx}:")
    print(f"  Finish Reason: {candidate.finish_reason}")
    print(f"  Safety Ratings: {candidate.safety_ratings}")

print("\n--- Response Text ---")
print(response.text)
