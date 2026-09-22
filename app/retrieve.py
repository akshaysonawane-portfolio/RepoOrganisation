import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from generate import generate_answer
from reranker import rerank
from repository_structure import (
    get_structure_context,
    get_version_files,
)
from entity_search import search_entities


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


chroma_client = chromadb.PersistentClient(
    path="chroma_db"
)


collection = chroma_client.get_collection(
    name="repository_code"
)


def get_entity_chunks(
    entity_files,
    question,
    max_chunks_per_file=2,
):
    """
    Retrieve relevant chunks from files identified
    by entity search.

    Instead of taking the first chunks from a file,
    use the LLM reranker to select the chunks most
    relevant to the question.
    """

    documents = []
    metadatas = []
    distances = []

    for file_path in entity_files:

        file_path = str(file_path)

        results = collection.get(
            where={
                "file": file_path
            },
            include=[
                "documents",
                "metadatas",
            ],
        )

        file_documents = results[
            "documents"
        ]

        file_metadatas = results[
            "metadatas"
        ]

        if not file_documents:
            continue

        if len(file_documents) <= max_chunks_per_file:

            selected_ids = list(
                range(
                    len(file_documents)
                )
            )

        else:

            selected_ids = rerank(
                question,
                file_documents,
                file_metadatas,
                top_k=max_chunks_per_file,
            )

        for index in selected_ids:

            documents.append(
                file_documents[index]
            )

            metadatas.append(
                file_metadatas[index]
            )

            distances.append(None)

    return (
        documents,
        metadatas,
        distances,
    )


def get_version_chunks(
    version_files,
    question,
    max_chunks_per_file=2,
):
    """
    Retrieve relevant chunks from files belonging
    to explicitly mentioned repository versions.

    For comparison questions, ensure that each
    requested version contributes at least one
    candidate chunk.
    """

    documents = []
    metadatas = []
    distances = []

    # Group files by version
    version_groups = {}

    for file_path in version_files:

        file_path = str(file_path)

        version = None

        for candidate in ["v1", "v2", "v3", "v4"]:
            if f"/{candidate}/" in file_path:
                version = candidate
                break

        if version is None:
            continue

        version_groups.setdefault(
            version,
            []
        ).append(file_path)

    # Retrieve chunks from each version
    for version, files in version_groups.items():

        version_candidates = []

        for file_path in files:

            results = collection.get(
                where={
                    "file": file_path
                },
                include=[
                    "documents",
                    "metadatas",
                ],
            )

            file_documents = results[
                "documents"
            ]

            file_metadatas = results[
                "metadatas"
            ]

            if not file_documents:
                continue

            # Rerank chunks within this file
            if len(file_documents) <= max_chunks_per_file:

                selected_ids = list(
                    range(
                        len(file_documents)
                    )
                )

            else:

                selected_ids = rerank(
                    question,
                    file_documents,
                    file_metadatas,
                    top_k=max_chunks_per_file,
                )

            for index in selected_ids:

                version_candidates.append(
                    (
                        file_documents[index],
                        file_metadatas[index],
                    )
                )

        if not version_candidates:
            continue

        # --------------------------------------------------
        # Guarantee at least one chunk from this version
        # --------------------------------------------------

        best_document, best_metadata = (
            version_candidates[0]
        )

        documents.append(
            best_document
        )

        metadatas.append(
            best_metadata
        )

        distances.append(None)

        # Add additional useful chunks from this version
        for document, metadata in version_candidates[1:]:

            if len(
                [
                    m
                    for m in metadatas
                    if f"/{version}/" in m["file"]
                ]
            ) >= max_chunks_per_file:
                break

            documents.append(
                document
            )

            metadatas.append(
                metadata
            )

            distances.append(None)

    return (
        documents,
        metadatas,
        distances,
    )


def search_repository(
    question: str,
    top_k: int = 10,
    distance_threshold: float = 1.4,
    rerank_top_k: int = 5,
):
    """
    Hybrid repository retrieval.

    Retrieval sources:

    1. Semantic vector search
    2. Entity/file-name search
    3. Version-aware retrieval
    4. Deduplication
    5. LLM reranking
    """

    # --------------------------------------------------
    # 1. Semantic retrieval
    # --------------------------------------------------

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question,
    )

    query_embedding = (
        response.data[0].embedding
    )

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = results[
        "documents"
    ][0]

    metadatas = results[
        "metadatas"
    ][0]

    distances = results[
        "distances"
    ][0]

    # --------------------------------------------------
    # 2. Apply semantic distance threshold
    # --------------------------------------------------

    filtered_documents = []
    filtered_metadatas = []
    filtered_distances = []

    for (
        document,
        metadata,
        distance,
    ) in zip(
        documents,
        metadatas,
        distances,
    ):

        if distance <= distance_threshold:

            filtered_documents.append(
                document
            )

            filtered_metadatas.append(
                metadata
            )

            filtered_distances.append(
                distance
            )

    # --------------------------------------------------
    # 3. Entity/file retrieval
    # --------------------------------------------------

    entity_files = search_entities(
        question
    )

    (
        entity_documents,
        entity_metadatas,
        entity_distances,
    ) = get_entity_chunks(
        entity_files,
        question,
        max_chunks_per_file=2,
    )

    # --------------------------------------------------
    # 4. Version-aware retrieval
    # --------------------------------------------------

    version_files = get_version_files(
        question
    )

    (
        version_documents,
        version_metadatas,
        version_distances,
    ) = get_version_chunks(
        version_files,
        question,
        max_chunks_per_file=2,
    )

    # --------------------------------------------------
    # 5. Combine all candidates
    # --------------------------------------------------

    combined = {}

    # Semantic results

    for (
        document,
        metadata,
        distance,
    ) in zip(
        filtered_documents,
        filtered_metadatas,
        filtered_distances,
    ):

        key = (
            metadata["file"],
            metadata["start_line"],
        )

        combined[key] = (
            document,
            metadata,
            distance,
        )

    # Entity results

    for (
        document,
        metadata,
        distance,
    ) in zip(
        entity_documents,
        entity_metadatas,
        entity_distances,
    ):

        key = (
            metadata["file"],
            metadata["start_line"],
        )

        if key not in combined:

            combined[key] = (
                document,
                metadata,
                distance,
            )

    # Version results

    for (
        document,
        metadata,
        distance,
    ) in zip(
        version_documents,
        version_metadatas,
        version_distances,
    ):

        key = (
            metadata["file"],
            metadata["start_line"],
        )

        if key not in combined:

            combined[key] = (
                document,
                metadata,
                distance,
            )

    # --------------------------------------------------
    # 6. No candidates
    # --------------------------------------------------

    if not combined:

        return [], [], []

    # --------------------------------------------------
    # 7. Convert combined candidates to lists
    # --------------------------------------------------

    combined_documents = []
    combined_metadatas = []
    combined_distances = []

    for (
        document,
        metadata,
        distance,
    ) in combined.values():

        combined_documents.append(
            document
        )

        combined_metadatas.append(
            metadata
        )

        combined_distances.append(
            distance
        )

    # --------------------------------------------------
    # 8. Final reranking
    # --------------------------------------------------

    selected_ids = rerank(
        question,
        combined_documents,
        combined_metadatas,
        top_k=rerank_top_k,
    )

    # --------------------------------------------------
    # 9. Return final results
    # --------------------------------------------------

    reranked_documents = [
        combined_documents[i]
        for i in selected_ids
    ]

    reranked_metadatas = [
        combined_metadatas[i]
        for i in selected_ids
    ]

    reranked_distances = [
        combined_distances[i]
        for i in selected_ids
    ]

    return (
        reranked_documents,
        reranked_metadatas,
        reranked_distances,
    )


if __name__ == "__main__":

    question = input(
        "\nAsk a question about the repository: "
    )

    (
        documents,
        metadatas,
        distances,
    ) = search_repository(
        question
    )

    print(
        "\n========== RETRIEVED CHUNKS ==========\n"
    )

    if not documents:

        print(
            "No sufficiently relevant repository "
            "context was found."
        )

    else:

        for i, (
            document,
            metadata,
            distance,
        ) in enumerate(
            zip(
                documents,
                metadatas,
                distances,
            ),
            start=1,
        ):

            print(
                f"--- Result {i} ---"
            )

            if distance is None:

                print(
                    "Retrieval: entity/version match"
                )

            else:

                print(
                    f"Distance: {distance}"
                )

            print(
                f"File: "
                f"{metadata['file']}"
            )

            print(
                f"Lines: "
                f"{metadata['start_line']}-"
                f"{metadata['end_line']}"
            )

            print(
                "\nCode:\n"
            )

            print(
                document[:1000]
            )

            print("\n")

    # --------------------------------------------------
    # Repository structure
    # --------------------------------------------------

    structure_context = (
        get_structure_context(
            question
        )
    )

    if structure_context:

        print(
            "\n========== STRUCTURE CONTEXT ==========\n"
        )

        print(
            structure_context
        )

    # --------------------------------------------------
    # Generate final answer
    # --------------------------------------------------

    if documents or structure_context:

        answer = generate_answer(
            question,
            documents,
            metadatas,
            structure_context=structure_context,
        )

    else:

        answer = (
            "I don't have enough information in the "
            "retrieved repository context to answer this."
        )

    print(
        "\n========== ANSWER ==========\n"
    )

    print(answer)