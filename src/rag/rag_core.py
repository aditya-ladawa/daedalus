"""
This file has been refactored into modular components.

Please use:
- src/rag/config.py: Configuration and Factory
- src/rag/ingest.py: For data ingestion (embedding)
- src/rag/query.py: For querying the database

To Run:
python src/rag/ingest.py
python src/rag/query.py
"""