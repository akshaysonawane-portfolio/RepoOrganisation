import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def rerank(
    question,
    documents,
    metadatas=None,
    top_k=3,
):
    """
    Rerank repository chunks based on how useful they are
    for answering the user's question.

    Metadata is included so the reranker knows which file
    each chunk came from.
    """

    candidates = []

    for i, document in enumerate(documents):

        metadata = {}

        if metadatas:
            metadata = metadatas[i]

        candidates.append(
            {
                "id": i,
                "file": metadata.get(
                    "file",
                    "unknown",
                ),
                "start_line": metadata.get(
                    "start_line",
                    "unknown",
                ),
                "end_line": metadata.get(
                    "end_line",
                    "unknown",
                ),
                "text": document[:4000],
            }
        )

    prompt = f"""
You are a reranking system for a code repository RAG system.

User question:

{question}

Your task is to rank repository chunks by how useful
they are for answering the question.

Consider:

1. Does the chunk contain the class, function, or
   concept mentioned in the question?

2. Does the chunk explain the relationship between
   entities mentioned in the question?

3. Does the chunk contain implementation details
   needed to answer the question?

4. Prefer implementation code over unrelated tests
   when the question asks how something works.

5. For relationship questions involving multiple
   entities, prefer chunks that connect those entities.

6. Do not rank a chunk highly merely because its
   filename contains a matching word.

Return ONLY valid JSON.

Format:

[
    {{
        "id": 0,
        "score": 9
    }},
    {{
        "id": 2,
        "score": 7
    }}
]

Score from 0 to 10.

0 = completely irrelevant
10 = directly useful for answering the question

Candidates:

{json.dumps(candidates, indent=2)}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt,
    )

    ranking = json.loads(
        response.output_text
    )

    ranking.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    selected_ids = [
        item["id"]
        for item in ranking[:top_k]
    ]

    return selected_ids