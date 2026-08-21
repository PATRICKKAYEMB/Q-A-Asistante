import logging
import os
import time
from typing import Dict, List

from django.conf import settings
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from .document_processor import DocumentProcessor

load_dotenv()


logger = logging.getLogger(__name__)


class AIServices:

  def __init__(self):
    self.llm = ChatGoogleGenerativeAI(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-1.5-flash",  
        temperature=0,
    )

    self.document_processor = DocumentProcessor()

    self.prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""
                You are an AI assistant that answers questions based only on the 
                context from the document:

                Context:
                {context}

                Question: {question}

                Instructions:
                1. Answer only based on the information provided in the context.
                2. If the answer cannot be found in the context, say 'I cannot answer the question based on the provided context.'
                3. Be concise but comprehensive in your answer.
                4. Quote relevant parts of the document when appropriate.
                5. Do not make assumptions or add information not present in the context.

                Answer:
            """,
    )

  def answer_question(self, document, question: str) -> Dict:
    start_time = time.time()

    try:
      if not document.processed or not document.vector_store_id:
        raise ValueError("Document is not processed yet")

      vector_store = self.document_processor.get_vector_store(
          document.vector_store_id
      )

      # Création de la chaîne RAG RetrievalQA
      qa_chain = RetrievalQA.from_chain_type(
          llm=self.llm,
          chain_type="stuff",
          retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
          chain_type_kwargs={"prompt": self.prompt_template},
          return_source_documents=True,
      )

      result = qa_chain({"query": question})

      processing_time = round(time.time() - start_time, 2)

      response = {
          "answer": result["result"],
          "source_documents": result.get("source_documents", []),
          "processing_time": processing_time,
      }

      logger.info(
          f"Question answered successfully for doc {document.id} in"
          f" {processing_time}s"
      )
      return response

    except Exception as e:
      logger.error(
          f"Error answering question for document {document.id}: {str(e)}"
      )
      raise