"""
Medical Knowledge System with BCFI.be Integration
Provides drug recognition, document learning, and knowledge enhancement
"""

import os
import re
import json
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: ChromaDB not available. Install with: pip install chromadb>=0.4.0")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: BeautifulSoup not available. Install with: pip install beautifulsoup4>=4.12.0")

logger = logging.getLogger(__name__)

@dataclass
class Drug:
    """Drug information structure"""
    generic_name: str
    brand_names: List[str]
    atc_code: str
    indications: str
    dosage_forms: List[str]
    contraindications: str = ""
    interactions: str = ""
    source: str = "manual"

@dataclass
class DocumentChunk:
    """Document chunk for knowledge base"""
    content: str
    document_type: str
    patient_id: Optional[str]
    department: str
    created_at: datetime
    metadata: Dict

class MedicalKnowledgeSystem:
    """Main medical knowledge system"""
    
    def __init__(self, db_path: str = "medical_knowledge.db"):
        self.db_path = db_path
        self.chroma_client = None
        self.drug_collection = None
        self.document_collection = None
        
        # Initialize databases
        self._init_sqlite_db()
        if CHROMADB_AVAILABLE:
            self._init_chroma_db()
        
        # Drug recognition patterns
        self.drug_patterns = {}
        self._load_drug_patterns()
    
    def _init_sqlite_db(self):
        """Initialize SQLite database for structured data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drugs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generic_name TEXT UNIQUE NOT NULL,
                brand_names TEXT,  -- JSON array
                atc_code TEXT,
                indications TEXT,
                dosage_forms TEXT,  -- JSON array
                contraindications TEXT,
                interactions TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                patient_id TEXT,
                department TEXT,
                content_hash TEXT UNIQUE,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Drug recognition patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drug_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                drug_id INTEGER,
                pattern_type TEXT,  -- 'exact', 'prefix', 'suffix', 'contains'
                FOREIGN KEY (drug_id) REFERENCES drugs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_chroma_db(self):
        """Initialize ChromaDB for vector storage"""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path="./chroma_db",
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Drug collection
            self.drug_collection = self.chroma_client.get_or_create_collection(
                name="belgian_drugs",
                metadata={"description": "Belgian drug database from BCFI"}
            )
            
            # Document collection
            self.document_collection = self.chroma_client.get_or_create_collection(
                name="medical_documents",
                metadata={"description": "Learned medical documents"}
            )
            
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self.chroma_client = None
    
    def add_drug(self, drug: Drug) -> bool:
        """Add a drug to the knowledge base"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO drugs 
                (generic_name, brand_names, atc_code, indications, dosage_forms, contraindications, interactions, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                drug.generic_name,
                json.dumps(drug.brand_names),
                drug.atc_code,
                drug.indications,
                json.dumps(drug.dosage_forms),
                drug.contraindications,
                drug.interactions,
                drug.source
            ))
            
            drug_id = cursor.lastrowid
            conn.commit()
            
            # Add to vector database
            if self.drug_collection:
                drug_text = f"{drug.generic_name} {' '.join(drug.brand_names)} {drug.atc_code} {drug.indications}"
                self.drug_collection.add(
                    documents=[drug_text],
                    metadatas=[{
                        "generic_name": drug.generic_name,
                        "atc_code": drug.atc_code,
                        "source": drug.source
                    }],
                    ids=[f"drug_{drug_id}"]
                )
            
            # Add recognition patterns
            self._add_drug_patterns(drug_id, drug.generic_name, drug.brand_names)
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding drug: {e}")
            return False
    
    def _add_drug_patterns(self, drug_id: int, generic_name: str, brand_names: List[str]):
        """Add recognition patterns for a drug"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = [
            (generic_name.lower(), 'exact'),
            (generic_name.lower()[:4], 'prefix') if len(generic_name) > 4 else None
        ]
        
        for brand in brand_names:
            patterns.extend([
                (brand.lower(), 'exact'),
                (brand.lower()[:4], 'prefix') if len(brand) > 4 else None
            ])
        
        for pattern, pattern_type in patterns:
            if pattern:
                cursor.execute('''
                    INSERT OR IGNORE INTO drug_patterns (pattern, drug_id, pattern_type)
                    VALUES (?, ?, ?)
                ''', (pattern, drug_id, pattern_type))
        
        conn.commit()
        conn.close()
    
    def search_drugs(self, query: str) -> List[Dict]:
        """Search for drugs by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT generic_name, brand_names, atc_code, indications, source
            FROM drugs 
            WHERE generic_name LIKE ? OR brand_names LIKE ?
            ORDER BY generic_name
        ''', (f'%{query}%', f'%{query}%'))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'generic_name': row[0],
                'brand_names': json.loads(row[1]) if row[1] else [],
                'atc_code': row[2],
                'indications': row[3],
                'source': row[4]
            })
        
        conn.close()
        return results
    
    def recognize_drugs_in_text(self, text: str) -> List[Dict]:
        """Recognize drugs mentioned in text"""
        recognized = []
        text_lower = text.lower()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all drug patterns
        cursor.execute('''
            SELECT p.pattern, p.pattern_type, d.generic_name, d.brand_names, d.atc_code
            FROM drug_patterns p
            JOIN drugs d ON p.drug_id = d.id
        ''')
        
        for pattern, pattern_type, generic, brands, atc in cursor.fetchall():
            if pattern_type == 'exact' and pattern in text_lower:
                recognized.append({
                    'found_text': pattern,
                    'generic_name': generic,
                    'brand_names': json.loads(brands) if brands else [],
                    'atc_code': atc,
                    'confidence': 0.9
                })
            elif pattern_type == 'prefix' and any(word.startswith(pattern) for word in text_lower.split()):
                recognized.append({
                    'found_text': pattern,
                    'generic_name': generic,
                    'brand_names': json.loads(brands) if brands else [],
                    'atc_code': atc,
                    'confidence': 0.7
                })
        
        conn.close()
        return recognized
    
    def learn_from_document(self, content: str, doc_type: str, patient_id: str = None, department: str = "General") -> Dict:
        """Learn from a medical document"""
        try:
            # Create content hash
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Store in SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata = {
                'document_type': doc_type,
                'patient_id': patient_id,
                'department': department,
                'word_count': len(content.split()),
                'created_at': datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT OR IGNORE INTO learned_documents 
                (document_type, patient_id, department, content_hash, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (doc_type, patient_id, department, content_hash, json.dumps(metadata)))
            
            doc_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Store in vector database
            if self.document_collection:
                # Chunk the document
                chunks = self._chunk_document(content)
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"doc_{doc_id}_chunk_{i}"
                    self.document_collection.add(
                        documents=[chunk],
                        metadatas=[metadata],
                        ids=[chunk_id]
                    )
            
            # Extract drugs from document
            drugs_found = self.recognize_drugs_in_text(content)
            
            return {
                'success': True,
                'document_id': doc_id,
                'chunks_created': len(chunks) if 'chunks' in locals() else 0,
                'drugs_found': len(drugs_found),
                'drugs': drugs_found
            }
            
        except Exception as e:
            logger.error(f"Error learning from document: {e}")
            return {'success': False, 'error': str(e)}
    
    def _chunk_document(self, content: str, chunk_size: int = 500) -> List[str]:
        """Split document into chunks for vector storage"""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def search_knowledge_base(self, query: str, doc_types: List[str] = None, limit: int = 5) -> List[Dict]:
        """Search the knowledge base for relevant information"""
        if not self.document_collection:
            return []
        
        try:
            results = self.document_collection.query(
                query_texts=[query],
                n_results=limit,
                where={"document_type": {"$in": doc_types}} if doc_types else None
            )
            
            formatted_results = []
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                formatted_results.append({
                    'content': doc,
                    'document_type': metadata.get('document_type'),
                    'department': metadata.get('department'),
                    'patient_id': metadata.get('patient_id'),
                    'relevance_score': 1 - results['distances'][0][i] if 'distances' in results else 0.5
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge base search error: {e}")
            return []
    
    def enhance_transcription(self, transcript: str, patient_id: str = None) -> Dict:
        """Enhance transcription with drug recognition and knowledge base"""
        try:
            # Recognize drugs
            drugs_found = self.recognize_drugs_in_text(transcript)
            
            # Search for relevant context
            context_results = self.search_knowledge_base(transcript, limit=3)
            
            # Enhance the transcript
            enhanced_transcript = transcript
            drug_corrections = []
            
            # Apply drug corrections
            for drug in drugs_found:
                if drug['confidence'] > 0.8:
                    # Replace with proper drug name
                    generic = drug['generic_name']
                    brands = ', '.join(drug['brand_names'][:2])  # Show top 2 brands
                    
                    correction = f"{generic}"
                    if brands:
                        correction += f" ({brands})"
                    
                    enhanced_transcript = enhanced_transcript.replace(
                        drug['found_text'], 
                        correction
                    )
                    drug_corrections.append({
                        'original': drug['found_text'],
                        'corrected': correction,
                        'atc_code': drug['atc_code']
                    })
            
            return {
                'enhanced_transcript': enhanced_transcript,
                'drugs_found': drugs_found,
                'drug_corrections': drug_corrections,
                'context_used': context_results,
                'enhancement_applied': len(drug_corrections) > 0 or len(context_results) > 0
            }
            
        except Exception as e:
            logger.error(f"Transcription enhancement error: {e}")
            return {
                'enhanced_transcript': transcript,
                'drugs_found': [],
                'drug_corrections': [],
                'context_used': [],
                'enhancement_applied': False,
                'error': str(e)
            }
    
    def _load_drug_patterns(self):
        """Load drug recognition patterns from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.pattern, p.pattern_type, d.generic_name
                FROM drug_patterns p
                JOIN drugs d ON p.drug_id = d.id
            ''')
            
            for pattern, pattern_type, generic in cursor.fetchall():
                if pattern_type not in self.drug_patterns:
                    self.drug_patterns[pattern_type] = {}
                self.drug_patterns[pattern_type][pattern] = generic
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading drug patterns: {e}")
    
    def import_from_bcfi(self, category_url: str = "/nl/chapters/1?frag=") -> Dict:
        """Import drugs from BCFI.be (Belgian drug database)"""
        if not BS4_AVAILABLE:
            return {'success': False, 'error': 'BeautifulSoup4 not available'}
        
        try:
            base_url = "https://www.bcfi.be"
            url = base_url + category_url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract drug information (this is a simplified example)
            # BCFI.be structure may vary, so this needs to be adapted
            drugs_imported = 0
            
            # Look for drug entries
            drug_entries = soup.find_all('div', class_=['drug-entry', 'medication'])
            
            for entry in drug_entries:
                try:
                    # Extract drug information (adapt based on actual BCFI structure)
                    generic_name = self._extract_text(entry, '.generic-name, .drug-name')
                    brand_names = self._extract_list(entry, '.brand-names, .commercial-names')
                    atc_code = self._extract_text(entry, '.atc-code')
                    indications = self._extract_text(entry, '.indications')
                    
                    if generic_name:
                        drug = Drug(
                            generic_name=generic_name,
                            brand_names=brand_names,
                            atc_code=atc_code or "",
                            indications=indications or "",
                            dosage_forms=[],
                            source="bcfi"
                        )
                        
                        if self.add_drug(drug):
                            drugs_imported += 1
                
                except Exception as e:
                    logger.warning(f"Error processing drug entry: {e}")
                    continue
            
            return {
                'success': True,
                'drugs_imported': drugs_imported,
                'source_url': url
            }
            
        except Exception as e:
            logger.error(f"BCFI import error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text(self, element, selector: str) -> str:
        """Extract text from HTML element"""
        try:
            found = element.select_one(selector)
            return found.get_text(strip=True) if found else ""
        except:
            return ""
    
    def _extract_list(self, element, selector: str) -> List[str]:
        """Extract list of text from HTML elements"""
        try:
            found = element.select(selector)
            return [item.get_text(strip=True) for item in found if item.get_text(strip=True)]
        except:
            return []
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM drugs')
            drug_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM learned_documents')
            doc_count = cursor.fetchone()[0]
            
            # Count brand names
            cursor.execute('SELECT brand_names FROM drugs WHERE brand_names IS NOT NULL')
            brand_count = 0
            for row in cursor.fetchall():
                try:
                    brands = json.loads(row[0])
                    brand_count += len(brands)
                except:
                    pass
            
            conn.close()
            
            # ChromaDB stats
            knowledge_chunks = 0
            if self.document_collection:
                try:
                    knowledge_chunks = self.document_collection.count()
                except:
                    pass
            
            return {
                'drug_count': drug_count,
                'brand_count': brand_count,
                'document_count': doc_count,
                'knowledge_chunks': knowledge_chunks
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'drug_count': 0,
                'brand_count': 0,
                'document_count': 0,
                'knowledge_chunks': 0
            }

def initialize_belgian_medical_system() -> MedicalKnowledgeSystem:
    """Initialize the medical knowledge system with some basic Belgian drugs"""
    system = MedicalKnowledgeSystem()
    
    # Add some common Belgian cardiovascular drugs
    common_drugs = [
        Drug(
            generic_name="Bisoprolol",
            brand_names=["Bisoprolol EG", "Bisoblock", "Bisoprolol Mylan"],
            atc_code="C07AB07",
            indications="Hypertensie, angina pectoris, hartfalen",
            dosage_forms=["tablet 2.5mg", "tablet 5mg", "tablet 10mg"]
        ),
        Drug(
            generic_name="Rivaroxaban",
            brand_names=["Xarelto"],
            atc_code="B01AF01",
            indications="Anticoagulatie, VTE preventie",
            dosage_forms=["tablet 10mg", "tablet 15mg", "tablet 20mg"]
        ),
        Drug(
            generic_name="Atorvastatine",
            brand_names=["Lipitor", "Atorvastatine EG", "Atorvastatine Mylan"],
            atc_code="C10AA05",
            indications="Hypercholesterolemie, cardiovasculaire preventie",
            dosage_forms=["tablet 10mg", "tablet 20mg", "tablet 40mg", "tablet 80mg"]
        ),
        Drug(
            generic_name="Metoprolol",
            brand_names=["Seloken", "Metoprolol EG"],
            atc_code="C07AB02",
            indications="Hypertensie, angina pectoris, hartfalen, post-MI",
            dosage_forms=["tablet 25mg", "tablet 50mg", "tablet 100mg"]
        ),
        Drug(
            generic_name="Amlodipine",
            brand_names=["Norvasc", "Amlodipine EG"],
            atc_code="C08CA01",
            indications="Hypertensie, angina pectoris",
            dosage_forms=["tablet 5mg", "tablet 10mg"]
        )
    ]
    
    for drug in common_drugs:
        system.add_drug(drug)
    
    logger.info(f"Initialized medical knowledge system with {len(common_drugs)} drugs")
    return system

# Global instance
_knowledge_system = None

def get_knowledge_system() -> MedicalKnowledgeSystem:
    """Get or create the global knowledge system instance"""
    global _knowledge_system
    if _knowledge_system is None:
        _knowledge_system = initialize_belgian_medical_system()
    return _knowledge_system

