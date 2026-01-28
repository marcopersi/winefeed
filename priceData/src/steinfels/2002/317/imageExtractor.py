from PIL import Image
import pytesseract

# Paths to the uploaded images (all screenshots in correct order)
image_paths = [
    "Bildschirmfoto 2025-08-02 um 01.21.37.png",
    "Bildschirmfoto 2025-08-02 um 01.21.45.png", 
    "Bildschirmfoto 2025-08-02 um 01.21.52.png",
    "Bildschirmfoto 2025-08-02 um 01.21.59.png",
    "Bildschirmfoto 2025-08-02 um 01.22.06.png",
    "Bildschirmfoto 2025-08-02 um 01.22.14.png",
    "Bildschirmfoto 2025-08-02 um 01.22.24.png",
    "Bildschirmfoto 2025-08-02 um 01.22.33.png",
    "Bildschirmfoto 2025-08-02 um 01.22.41.png",
    "Bildschirmfoto 2025-08-02 um 01.22.48.png",
    "Bildschirmfoto 2025-08-02 um 01.22.57.png",
    "Bildschirmfoto 2025-08-02 um 01.23.05.png",
    "Bildschirmfoto 2025-08-02 um 01.23.13.png",
]

# Retry OCR using the default English language (which should be available)
extracted_texts_en = []
for i, path in enumerate(image_paths, 1):
    try:
        print(f"Processing image {i}/{len(image_paths)}: {path}")
        img = Image.open(path)
        text = pytesseract.image_to_string(img)  # default language (eng)
        extracted_texts_en.append(text)
        print(f"  Extracted {len(text)} characters")
    except FileNotFoundError:
        print(f"  ERROR: File not found - {path}")
    except Exception as e:
        print(f"  ERROR processing {path}: {e}")

# Combine the extracted text
combined_text_en = "\n\n---\n\n".join(extracted_texts_en)

# Save to TXT file
output_txt_path_en = "weinauktion_extracted_en.txt"
with open(output_txt_path_en, "w", encoding="utf-8") as f:
    f.write(combined_text_en)
print(f"Extracted text saved to {output_txt_path_en}")
