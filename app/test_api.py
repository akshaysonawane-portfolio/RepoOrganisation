import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

response = client.embeddings.create(
    model="text-embedding-3-small",
    input="How does the database connection work?"
)

embedding = response.data[0].embedding
print("Embedding created successfully!")
print("Vector dimensions:", len(embedding))