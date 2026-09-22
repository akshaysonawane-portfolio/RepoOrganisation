from pathlib import Path


def chunk_file(
    file_path: Path,
    content: str,
    chunk_size: int = 3000,
    overlap: int = 300,
):
    chunks = []

    lines = content.splitlines(keepends=True)

    current_chunk = []
    current_size = 0
    start_line = 1

    for line_number, line in enumerate(lines, start=1):

        if current_chunk and current_size + len(line) > chunk_size:

            chunks.append({
                "content": "".join(current_chunk),
                "file": str(file_path),
                "start_line": start_line,
                "end_line": line_number - 1,
            })

            # Keep a small amount of previous context
            overlap_text = ""
            overlap_size = 0

            for previous_line in reversed(current_chunk):
                if overlap_size + len(previous_line) > overlap:
                    break

                overlap_text = previous_line + overlap_text
                overlap_size += len(previous_line)

            current_chunk = [overlap_text]
            current_size = len(overlap_text)
            start_line = max(1, line_number - len(current_chunk))

        current_chunk.append(line)
        current_size += len(line)

    if current_chunk:
        chunks.append({
            "content": "".join(current_chunk),
            "file": str(file_path),
            "start_line": start_line,
            "end_line": len(lines),
        })

    return chunks
