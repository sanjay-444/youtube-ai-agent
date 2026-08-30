from app.services.pdf_generator import clean_text


text = "five-day 17-member anti-corruption high-level"


print("BEFORE:")
print(text)

print()

print("AFTER:")
print(clean_text(text))