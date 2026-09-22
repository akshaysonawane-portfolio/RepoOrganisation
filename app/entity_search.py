from pathlib import Path


REPO_PATH = Path(
    "/home/ska/Desktop/project-tmc/ska-tmc-common"
)

IGNORED_DIRECTORIES = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    ".make",
    "charts",
}


def normalize_name(name: str) -> str:
    """
    Convert a Python class/entity name into a filename-like form.

    Example:
        TmcComponentManager
        -> tmc_component_manager
    """

    result = ""

    for i, char in enumerate(name):

        if char.isupper() and i > 0:
            result += "_"

        result += char.lower()

    return result


def search_entities(question: str):
    """
    Find repository files whose names correspond to entities
    mentioned in the question.
    """

    words = question.replace(
        "?", ""
    ).replace(
        ",", " "
    ).split()

    candidates = []

    for word in words:

        # Ignore normal English words
        if len(word) < 4:
            continue

        normalized = normalize_name(word)

        filename = f"{normalized}.py"

        for path in REPO_PATH.rglob(filename):

            if any(
                part in IGNORED_DIRECTORIES
                for part in path.parts
            ):
                continue

            candidates.append(path)

    # Remove duplicates
    return list(dict.fromkeys(candidates))


if __name__ == "__main__":

    question = input("Question: ")

    results = search_entities(question)

    print("\n========== ENTITY RESULTS ==========\n")

    for path in results:
        print(path.relative_to(REPO_PATH))