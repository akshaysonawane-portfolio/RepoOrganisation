import os

import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.PersistentClient(
    path="chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="repository_code"
)


def create_embeddings(texts, batch_size=5):

    all_embeddings = []

    for i in range(0, len(texts), batch_size):

        batch = texts[i:i + batch_size]

        print(
            f"Creating embeddings for "
            f"{i + 1}-{min(i + batch_size, len(texts))} "
            f"of {len(texts)} chunks..."
        )

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )

        embeddings = [
            item.embedding
            for item in response.data
        ]

        all_embeddings.extend(embeddings)

    return all_embeddings

def store_chunks(chunks):

    texts = [chunk["content"] for chunk in chunks]

    embeddings = create_embeddings(texts)

    ids = [
        f"{chunk['file']}:{chunk['start_line']}"
        for chunk in chunks
    ]

    metadatas = [
        {
            "file": chunk["file"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"Stored {len(chunks)} chunks.")