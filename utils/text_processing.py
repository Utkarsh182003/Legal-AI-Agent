import re
from typing import List

def clean_text(text: str) -> str:
    """
    Performs basic cleaning on extracted text:
    - Removes common header/footer patterns (simplified for now).
    - Removes excessive whitespace and newline characters.
    - Normalizes hyphens and other tricky characters.
    """
    cleaned_text = re.sub(r'Page \d+ of \d+|\[\s*\d+\s*\]', '', text, flags=re.IGNORECASE)

    cleaned_text = cleaned_text.replace('\xa0', ' ').replace('\u200b', '')

    # Normalize multiple newlines and spaces
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text) 
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)     
    cleaned_text = cleaned_text.strip()                     


    return cleaned_text

def split_into_sentences(text: str) -> List[str]:
    """
    Splits the given text into a list of sentences using a simple regex-based approach.
    This replaces NLTK's sent_tokenize to avoid NLTK download issues.
    It handles common sentence endings like '.', '!', '?' followed by a space or end of string.
    """
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n\n', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def split_into_paragraphs(text: str) -> List[str]:
    """
    Splits the given text into a list of paragraphs based on double newlines.
    Filters out empty paragraphs.
    """
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]

if __name__ == "__main__":
    sample_text = """
    This is the first paragraph. It contains multiple sentences.
    This is line one.
    This is line two.

    This is the second paragraph.
    It has more content. Page 1 of 10. [5]
    A final sentence! Is this working? Yes.
    """

    print("Original Text:\n", sample_text)

    cleaned = clean_text(sample_text)
    print("\nCleaned Text:\n", cleaned)

    sentences = split_into_sentences(cleaned)
    print("\nSentences:")
    for i, sent in enumerate(sentences):
        print(f"{i}: {sent}")

    paragraphs = split_into_paragraphs(cleaned)
    print("\nParagraphs:")
    for i, para in enumerate(paragraphs):
        print(f"{i}: {para[:50]}...") # Print first 50 chars of each paragraph
