"""
Data Loader for RAG System
Handles loading and preprocessing of documents from various sources.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
import json
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Document data structure"""
    content: str
    metadata: Dict[str, Any]
    doc_id: str
    doc_type: str
    source: str
    
    @property
    def page_content(self) -> str:
        """Compatibility property for LangChain integration"""
        return self.content

class DataLoader:
    """Data loader for RAG system"""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or settings.data_dir
        self.text_dir = os.path.join(self.data_dir, "text_files")
        self.pdf_dir = os.path.join(self.data_dir, "pdf")
        logger.info(f"DataLoader initialized with data_dir: {self.data_dir}")
    
    def load_all_documents(self) -> List[Document]:
        """Load all documents from data directory"""
        documents = []
        
        try:
            # Load text files
            if os.path.exists(self.text_dir):
                text_docs = self._load_text_files()
                documents.extend(text_docs)
                logger.info(f"Loaded {len(text_docs)} text documents")
            
            # Load PDF files
            if os.path.exists(self.pdf_dir):
                pdf_docs = self._load_pdf_files()
                documents.extend(pdf_docs)
                logger.info(f"Loaded {len(pdf_docs)} PDF documents")
            
            logger.info(f"Total documents loaded: {len(documents)}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            return []
    
    def _load_text_files(self) -> List[Document]:
        """Load text files from text_files directory"""
        documents = []
        
        if not os.path.exists(self.text_dir):
            return documents
        
        for file_path in Path(self.text_dir).glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                document = Document(
                    content=content,
                    metadata={
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "file_size": os.path.getsize(file_path),
                        "created_time": os.path.getctime(file_path),
                        "modified_time": os.path.getmtime(file_path),
                        "doc_type": "text"
                    },
                    doc_id=file_path.stem,
                    doc_type="text",
                    source="text_files"
                )
                
                documents.append(document)
                
            except Exception as e:
                logger.error(f"Error loading text file {file_path}: {e}")
        
        return documents
    
    def _load_pdf_files(self) -> List[Document]:
        """Load PDF files from pdf directory"""
        documents = []
        
        if not os.path.exists(self.pdf_dir):
            return documents
        
        # Placeholder for PDF loading - would need PyPDF2 or similar
        # For now, return empty list
        logger.info("PDF loading not implemented - returning empty list")
        
        return documents
    
    def filter_documents(self, documents: List[Document], 
                        min_length: int = 100, 
                        max_length: Optional[int] = None) -> List[Document]:
        """Filter documents by length"""
        filtered = []
        
        for doc in documents:
            if len(doc.content) >= min_length:
                if max_length is None or len(doc.content) <= max_length:
                    filtered.append(doc)
        
        logger.info(f"Filtered {len(documents)} to {len(filtered)} documents")
        return filtered
    
    def split_documents(self, documents: List[Document], 
                       chunk_size: int = 1000, 
                       chunk_overlap: int = 100) -> List[Document]:
        """Split documents into chunks"""
        chunked_docs = []
        
        for doc in documents:
            content = doc.content
            
            # Simple chunking - in production, use more sophisticated chunking
            chunks = []
            start = 0
            
            while start < len(content):
                end = start + chunk_size
                chunk = content[start:end]
                
                chunk_doc = Document(
                    content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_index": len(chunks),
                        "total_chunks": (len(content) + chunk_size - 1) // chunk_size,
                        "doc_id": f"{doc.doc_id}_chunk_{len(chunks)}",
                        "doc_type": "chunk"
                    },
                    doc_id=f"{doc.doc_id}_chunk_{len(chunks)}",
                    doc_type="chunk",
                    source=doc.source
                )
                
                chunks.append(chunk_doc)
                start = end - chunk_overlap  # Add overlap
        
        chunked_docs.extend(chunks)
        logger.info(f"Split {len(documents)} documents into {len(chunked_docs)} chunks")
        return chunked_docs

# Global function for backward compatibility
def load_all_documents(data_dir: Optional[str] = None) -> List[Document]:
    """Load all documents from data directory"""
    loader = DataLoader(data_dir)
    return loader.load_all_documents()