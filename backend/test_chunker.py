from app.services.chunker import chunk_text


text = "A " * 30000

chunks = chunk_text(text)

print("Number of chunks:", len(chunks))

for index, chunk in enumerate(chunks):

    print(
        f"Chunk {index + 1}: "
        f"{len(chunk)} characters"
    )