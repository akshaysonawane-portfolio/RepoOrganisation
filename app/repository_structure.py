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
    ".coverage",
    "node_modules",
    ".make",
    "charts",
}


SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".rst",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
}


def build_repository_structure():
    """
    Build a lightweight representation of the repository
    structure.
    """

    structure = []

    for path in REPO_PATH.rglob("*"):

        if any(
            part in IGNORED_DIRECTORIES
            for part in path.parts
        ):
            continue

        if not path.is_file():
            if path.is_dir():
                structure.append(
                    {
                        "type": "directory",
                        "path": str(
                            path.relative_to(REPO_PATH)
                        ),
                    }
                )
            continue

        if path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        structure.append(
            {
                "type": "file",
                "path": str(
                    path.relative_to(REPO_PATH)
                ),
            }
        )

    return structure


def search_structure(question: str, structure):
    """
    Find repository structure entries relevant to
    the question.
    """

    question_lower = question.lower()

    search_terms = []

    if "v1" in question_lower:
        search_terms.append("v1")

    if "v2" in question_lower:
        search_terms.append("v2")

    if "v3" in question_lower:
        search_terms.append("v3")

    if "v4" in question_lower:
        search_terms.append("v4")

    if "test" in question_lower:
        search_terms.extend(
            ["test", "tests"]
        )

    if "python" in question_lower:
        search_terms.append(".py")

    if "src" in question_lower:
        search_terms.append("src")

    matches = []

    for item in structure:

        path_lower = item["path"].lower()

        if any(
            term in path_lower
            for term in search_terms
        ):
            matches.append(item)

    return matches


def get_structure_context(question: str):
    """
    Return relevant repository structure information
    for the question.
    """

    structure = build_repository_structure()

    matches = search_structure(
        question,
        structure,
    )

    if not matches:
        return ""

    context_lines = [
        "REPOSITORY STRUCTURE INFORMATION:"
    ]

    for item in matches[:30]:
        context_lines.append(
            f"{item['type']}: {item['path']}"
        )

    return "\n".join(context_lines)


def get_version_files(question: str):
    """
    Detect explicitly mentioned repository versions
    and return source files belonging to those versions.

    Example:

        What is the difference between v1, v2, v3 and v4?

    returns files from:

        src/ska_tmc_common/v1
        src/ska_tmc_common/v2
        src/ska_tmc_common/v3
        src/ska_tmc_common/v4
    """

    question_lower = question.lower()

    versions = []

    for version in ["v1", "v2", "v3", "v4"]:
        if version in question_lower:
            versions.append(version)

    if not versions:
        return []

    results = []

    for version in versions:

        version_path = (
            REPO_PATH
            / "src"
            / "ska_tmc_common"
            / version
        )

        if not version_path.exists():
            continue

        for path in version_path.rglob("*"):

            if not path.is_file():
                continue

            if path.suffix not in SUPPORTED_EXTENSIONS:
                continue

            if any(
                part in IGNORED_DIRECTORIES
                for part in path.parts
            ):
                continue

            results.append(path)

    return list(
        dict.fromkeys(results)
    )


if __name__ == "__main__":

    question = input(
        "\nQuestion: "
    )

    print(
        "\n========== STRUCTURE RESULTS ==========\n"
    )

    structure_context = get_structure_context(
        question
    )

    if structure_context:
        print(structure_context)
    else:
        print(
            "No relevant structure information found."
        )

    print(
        "\n========== VERSION FILES ==========\n"
    )

    version_files = get_version_files(
        question
    )

    if version_files:

        for path in version_files:
            print(
                path.relative_to(REPO_PATH)
            )

    else:
        print(
            "No explicit repository versions found."
        )