

import os
import numpy as np
from google import genai
from dotenv import load_dotenv


load_dotenv()


client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

def call_llm(prompt):

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


def get_embedding(text):

    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text
    )

    
    embedding = response.embeddings[0].values

   
    return np.array(embedding, dtype=np.float32)


def fixed_size_chunk(text, chunk_size=2000):

    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i : i + chunk_size])

    return chunks


if __name__ == "__main__":

    print("=== Testing call_llm ===")

    prompt = "In a few words, what is the meaning of life?"

    print(f"Prompt: {prompt}")

    response = call_llm(prompt)

    print(f"Response: {response}")


    print("\n=== Testing embedding function ===")

    text1 = "The quick brown fox jumps over the lazy dog."
    text2 = "Python is a popular programming language for data science."

    gemini_emb1 = get_embedding(text1)
    gemini_emb2 = get_embedding(text2)

    print(f"Gemini Embedding 1 shape: {gemini_emb1.shape}")

    similarity = np.dot(gemini_emb1, gemini_emb2)

    print(f"Gemini similarity between texts: {similarity:.4f}")
