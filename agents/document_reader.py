import os
import fitz 
from docx import Document
from pydantic_ai import Agent
from typing import List
from pydantic import ValidationError
import uuid # For generating unique IDs

from models.document_models import DocumentInput, DocumentContent, Paragraph, Sentence
from utils.text_processing import clean_text, split_into_sentences, split_into_paragraphs

class DocumentReaderAgent(Agent):
    """
    Agent responsible for reading various legal document formats (PDF, DOCX, TXT),
    extracting their raw text content, and performing initial preprocessing.
    Now also segments text into structured paragraphs and sentences.
    """
    def run(self, input: DocumentInput) -> DocumentContent:
        """
        Reads the document from the given file path and returns its cleaned text content,
        segmented into paragraphs and sentences.

        Args:
            input (DocumentInput): An instance of DocumentInput containing the file path.

        Returns:
            DocumentContent: An instance containing the extracted text, file name, file type,
                             and structured paragraphs with sentences.

        Raises:
            ValueError: If the file type is unsupported or reading fails.
        """
        file_path = input.file_path
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1]
        file_type = file_extension.lstrip('.').lower()
        text_content = ""

        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        print(f"Attempting to read file: {file_name} (Type: {file_type})")

        try:
            if file_type == 'pdf':
                doc = fitz.open(file_path)
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text_content += page.get_text("text") 
                doc.close()
            elif file_type == 'docx':
                doc = Document(file_path)
                for paragraph_obj in doc.paragraphs:
                    text_content += paragraph_obj.text + "\n"
            elif file_type == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            else:
                raise ValueError(f"Unsupported file type: {file_type}. Supported types are .pdf, .docx, .txt.")
        except Exception as e:
            raise ValueError(f"Error reading file {file_name}: {e}")

        # Apply text cleaning utilities
        cleaned_text = clean_text(text_content)
        
        # Segment into structured paragraphs and sentences
        paragraphs_raw = split_into_paragraphs(cleaned_text)
        structured_paragraphs: List[Paragraph] = []
        for p_idx, p_text in enumerate(paragraphs_raw):
            sentences_raw = split_into_sentences(p_text)
            structured_sentences: List[Sentence] = [
                Sentence(text=s_text, index=s_idx)
                for s_idx, s_text in enumerate(sentences_raw)
            ]
            structured_paragraphs.append(
                Paragraph(text=p_text, index=p_idx, sentences=structured_sentences)
            )

        print(f"Successfully extracted and cleaned text from {file_name}.")
        
        # Return DocumentContent with structured paragraphs
        return DocumentContent(
            text_content=cleaned_text,
            file_name=file_name,
            file_type=file_type,
            paragraphs=structured_paragraphs 
        )

