import logging
import os
from typing import List, Tuple

from django.conf import settings
from docx import Document as DocxDocument
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2

load_dotenv()


logger = logging.getLogger(__name__)


class DocumentProcessor:

  def __init__(self):
    self.embedding = GoogleGenerativeAIEmbeddings(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        model="models/embedding-001",  # Spécifier le modèle d'embedding
    )

   
    self.text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, length_function=len
    )

  def extract_text_from_file(self, file_path: str, file_type: str) -> str:
    try:
      file_type = file_type.lower().strip()
      if file_type == "txt":
        return self.extract_from_txt(file_path)
      elif file_type == "pdf":
        return self.extract_from_pdf(file_path)
      elif file_type == "docx":
        return self.extract_from_docx(file_path)
      else:
        raise ValueError(f"Format non supporté : {file_type}")

    except Exception as e:
      logger.error(
          f"Erreur lors de l'extraction du texte dans le fichier"
          f" {file_path}: {str(e)}"
      )
      raise

  def extract_from_txt(self, file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
      return file.read()

  def extract_from_pdf(self, file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as file:
      pdf_reader = PyPDF2.PdfReader(file)
      for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
          text += extracted + "\n"
    return text

  def extract_from_docx(self, file_path: str) -> str:
    doc = DocxDocument(file_path)
    text = ""
    for paragraph in doc.paragraphs:
      text += paragraph.text + "\n"
    return text

  def document_process(self, document):
    try:
      file_path = document.file.path

      text = self.extract_text_from_file(file_path, document.file_type)

      if not text or not text.strip():
        raise ValueError("Pas de texte trouvé dans le document")

      chunks = self.text_splitter.split_text(text)

      vector_store_id = f"doc_{document.id}"
      persist_directory = settings.CHROMA_PERSIST_DIRECTORY

      vector_store = Chroma.from_texts(
          texts=chunks,
          embedding=self.embedding,
          persist_directory=persist_directory,
          collection_name=vector_store_id,
      )
      document.vector_store_id = vector_store_id
      document.processed = True
      document.save()

    except Exception as e:
      logger.error(
          f"Erreur lors du traitement du document {document.id}: {str(e)}"
      )
      raise

  def get_vector_store(self, vector_store_id: str):
    try:
      persist_directory = settings.CHROMA_PERSIST_DIRECTORY

      return Chroma(
          persist_directory=persist_directory,
          embedding_function=self.embedding,
          collection_name=vector_store_id,
      )
    except Exception as e:
      logger.error(
          f"Erreur lors du chargement de la base vectorielle"
          f" {vector_store_id}: {str(e)}"
      )
      raise