import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def generate_answer(
    question,
    retrieved_documents,
    metadatas,
    structure_context="",
):

    context_parts = []

    # Add semantic/code retrieval results
    for i, (document, metadata) in enumerate(
        zip(
            retrieved_documents,
            metadatas,
        ),
        start=1,
    ):

        source = f"""
SOURCE {i}

File:
{metadata['file']}

Lines:
{metadata['start_line']}-{metadata['end_line']}

Code:
{document}
"""

        context_parts.append(source)

    context = "\n".join(context_parts)

    # Add repository structure information
    if structure_context:
        context += f"""

REPOSITORY STRUCTURE

{structure_context}
"""

    prompt = f"""
You are a software engineer helping a developer
understand a code repository.

Answer the user's question ONLY using the
repository context provided below.

Rules:

1. Do not use your general knowledge about the project.

2. Do not invent information.

3. If the context does not contain enough information,
say:
"I don't have enough information in the retrieved
repository context to answer this."

4. When making a factual claim based on code context,
cite the relevant source using [Source N].

5. When making a factual claim based on repository
structure, cite it as [Structure].

6. At the end, provide a Sources section listing
the files and line numbers used.

7. Keep the answer concise but technically useful.

Repository context:

{context}

User question:

{question}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt,
    )

    return response.output_text