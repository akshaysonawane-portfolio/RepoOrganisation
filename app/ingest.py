import os
from pathlib import Path
from chunker import chunk_file
from vector_store import store_chunks

SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".rst",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
}

ALLOWED_ROOTS = {
    "src",
    "tests",
}

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


def get_files(repo_path: str):

    repo = Path(repo_path)
    files = []

    for path in repo.rglob("*"):

        if not path.is_file():
            continue

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        relative = path.relative_to(repo)

        # Include README / project documentation
        if len(relative.parts) == 1:
            if path.name.lower().startswith("readme"):
                files.append(path)
            continue

        # Only index src/ and tests/
        if relative.parts[0] not in ALLOWED_ROOTS:
            continue

        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)

    return files

def read_file(file_path: Path):
    try:
        return file_path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        print(f"Skipping non-text file: {file_path}")
        return None




def process_repository(repo_path: str):

    files = get_files(repo_path)

    all_chunks = []

    for file in files:

        content = read_file(file)

        if not content:
            continue

        chunks = chunk_file(file, content)

        all_chunks.extend(chunks)

        print(
            f"{file} → {len(chunks)} chunks"
        )

    print(f"\nTotal chunks: {len(all_chunks)}")

    store_chunks(all_chunks)

if __name__ == "__main__":

    repo_path = input("Enter local repository path: ")

    process_repository(repo_path)