import numpy as np
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(
   api_key=os.environ.get("GROQ_API_KEY"),
)



def get_embedding(text):

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    embedding = response.embeddings[0].values

    return np.array(
        embedding,
        dtype=np.float32
    )



def fixed_size_chunk(text):

    sentences = text.split(".")

    chunks = []

    for sentence in sentences:

        sentence = sentence.strip()

        if sentence:
            chunks.append(sentence)

    return chunks


if __name__ == "__main__":

    text = """
    Artificial Intelligence is transforming industries.
    Semantic search retrieves information based on meaning.
    Embeddings convert text into vectors.
    """

    chunks = fixed_size_chunk(text)

    for chunk in chunks:

        embedding = get_embedding(chunk)

        print("Chunk:", chunk)

        print("Embedding shape:", embedding.shape)

        print()