"""
Data Ingestion Script for LightRAG
"""
import asyncio
import time
from pathlib import Path
from datetime import datetime

# Import configuration
from config import get_rag_instance, WORKING_DIR, LLM_MODEL, EMBEDDING_MODEL, EMBEDDING_DIM

TIMING_REPORT_DIR = "src/rag/time_it"

# =============================================================================
# TIMING REPORT LOGIC
# =============================================================================

def get_next_report_number(report_dir: str) -> int:
    """Get the next available report number."""
    report_path = Path(report_dir)
    if not report_path.exists():
        return 0
    
    existing = list(report_path.glob("timing_report_*.md"))
    if not existing:
        return 0
    
    numbers = []
    for f in existing:
        try:
            num = int(f.stem.split("_")[-1])
            numbers.append(num)
        except ValueError:
            continue
    
    return max(numbers) + 1 if numbers else 0


def generate_timing_report(
    timing_data: list[dict],
    total_time: float,
    report_dir: str = TIMING_REPORT_DIR
) -> str:
    """Generate a markdown timing report."""
    
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    
    report_num = get_next_report_number(report_dir)
    report_file = report_path / f"timing_report_{report_num}.md"
    
    # Build report content
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# LightRAG Ingestion Timing Report

**Generated**: {now}  
**Report #**: {report_num}

## Configuration

| Setting | Value |
|---------|-------|
| LLM Model | `{LLM_MODEL}` |
| Embedding Model | `{EMBEDDING_MODEL}` |
| Embedding Dimensions | {EMBEDDING_DIM} |
| Working Directory | `{WORKING_DIR}` |

## File Processing Times

| # | File | Size (chars) | Time (s) | Status |
|---|------|--------------|----------|--------|
"""
    
    for i, data in enumerate(timing_data, 1):
        status = "✅" if data.get("success", True) else "❌"
        report += f"| {i} | `{data['file']}` | {data['size']:,} | {data['time']:.2f} | {status} |\n"
    
    # Summary
    total_chars = sum(d['size'] for d in timing_data)
    avg_time = total_time / len(timing_data) if timing_data else 0
    
    report += f"""
## Summary

| Metric | Value |
|--------|-------|
| Total Files | {len(timing_data)} |
| Total Characters | {total_chars:,} |
| Total Time | {total_time:.2f}s |
| Average Time/File | {avg_time:.2f}s |
| Processing Rate | {total_chars/total_time:.0f} chars/s |

## Notes

- Batch insert used (single call for all files)
- Entity merging enabled across all documents
- Times are wall-clock measurements
"""
    
    # Write report
    report_file.write_text(report)
    print(f"\n📊 Timing report saved: {report_file}")
    
    return str(report_file)


# =============================================================================
# INGESTION LOGIC
# =============================================================================

async def ingest_directory(
    rag, 
    directory: str, 
    pattern: str = "processed_*.md",
    generate_report: bool = True
):
    """
    Ingest all matching files from a directory in ONE batch.
    """
    print("\n" + "="*60)
    print("📂 BATCH INGESTION")
    print("="*60)
    
    files = sorted(Path(directory).glob(pattern))
    
    if not files:
        print(f"❌ No files found matching '{pattern}' in {directory}")
        return
    
    print(f"📍 Directory: {directory}")
    print(f"🔍 Pattern: {pattern}")
    print(f"📄 Files found: {len(files)}")
    print("-"*60)
    
    # Read all files and collect timing data
    texts = []
    ids = []
    timing_data = []
    
    for i, f in enumerate(files, 1):
        file_start = time.time()
        print(f"[{i}/{len(files)}] Reading: {f.name}")
        
        content = f.read_text(encoding="utf-8")
        file_id = f.stem
        
        texts.append(content)
        ids.append(file_id)
        
        file_time = time.time() - file_start
        timing_data.append({
            "file": f.name,
            "id": file_id,
            "size": len(content),
            "time": file_time,
            "success": True
        })
    
    # Batch insert
    print("\n" + "-"*60)
    print("🔄 Starting batch insert (entity extraction + embedding)...")
    print("   This may take a while for large documents...")
    print("-"*60)
    
    insert_start = time.time()
    await rag.ainsert(texts, ids=ids)
    insert_time = time.time() - insert_start
    
    # Update timing data with insert time (distributed)
    per_file_insert_time = insert_time / len(files)
    for data in timing_data:
        data["time"] += per_file_insert_time
    
    total_time = sum(d["time"] for d in timing_data)
    
    # Print summary
    print(f"\n✅ INGESTION COMPLETE in {total_time:.2f}s")
    
    # Generate report
    if generate_report:
        generate_timing_report(timing_data, total_time)



async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest documents into LightRAG")
    parser.add_argument("--input", "-i", default="src/rag/files_to_embed", help="Directory containing files to ingest")
    parser.add_argument("--db", "-d", default=None, help="Output directory for LightRAG database (config default if not set)")
    args = parser.parse_args()

    # Initialize RAG with optional custom DB path
    rag = await get_rag_instance(working_dir=args.db)
    
    # Ingest files from specified input
    await ingest_directory(rag, args.input, "processed_*.md")
    
    await rag.finalize_storages()
    print("✅ Ingestion finished and resources cleaned up.")

if __name__ == "__main__":
    asyncio.run(main())


# # Usage Examples:
# # Default (uses src/rag/files_to_embed and config's default DB):
# # bash
# python src/rag/ingest.py
# # Custom DB (e.g., lightrag_data_2):
# # bash
# python src/rag/ingest.py --db ./lightrag_data_2
# # Custom Input & DB:
# # bash
# python src/rag/ingest.py --input ./new_data --db ./new_db