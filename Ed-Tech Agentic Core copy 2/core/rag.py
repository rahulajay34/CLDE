import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import pypdf
from typing import List, Optional
import hashlib
from core.logger import logger

class RAGManager:
    def __init__(self, persist_directory="./storage/chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize Client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize Embedding Function
        # Using a lightweight local model
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        # Create/Get Collection
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn
        )
        logger.info("RAG Manager Initialized.")

    def ingest_document(self, file_path: str, filename: str) -> bool:
        """
        Parses a PDF or Text file and adds chunks to the vector store.
        """
        try:
            text = ""
            if filename.endswith(".pdf"):
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            if not text.strip():
                logger.warning(f"Empty text in {filename}")
                return False

            # Chunking (Simple overlap)
            chunks = self._chunk_text(text)
            
            # IDs based on content hash to prevent duplicates (naive)
            ids = [hashlib.md5(f"{filename}_{i}".encode()).hexdigest() for i in range(len(chunks))]
            metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]
            
            self.collection.upsert(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Ingested {len(chunks)} chunks from {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}")
            return False

    def retrieve_context(self, query: str, k: int = 3, threshold: float = 1.5) -> str:
        """
        Retrieves top k relevant chunks with a distance threshold.
        Lower distance = more similar (for L2/Euclidean). 
        Adjust threshold based on embedding model.
        """
        try:
            # Request distances
            results = self.collection.query(
                query_texts=[query],
                n_results=k * 2 # Fetch more to filter potential low quality ones
            )
            
            if not results["documents"]:
                return ""
            
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
            
            filtered_results = []
            
            for i, doc in enumerate(docs):
                dist = distances[i]
                if dist <= threshold:
                    source = metadatas[i].get("source", "Unknown")
                    filtered_results.append((dist, f"[Source: {source}]\n{doc}\n\n"))
            
            # Sort by distance (asc) and take top k
            filtered_results.sort(key=lambda x: x[0])
            top_results = filtered_results[:k]
            
            if not top_results:
                return ""
                
            return "".join([r[1] for r in top_results]).strip()

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += (chunk_size - overlap)
        return chunks

    def clear_database(self):
        try:
            self.client.delete_collection("knowledge_base")
            self.collection = self.client.create_collection(
                name="knowledge_base",
                embedding_function=self.embedding_fn
            )
        except Exception as e:
            logger.error(f"Failed to clear DB: {e}")
