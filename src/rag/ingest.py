"""
Ingestion Script for LightRAG with Incremental Support

Features:
- Batch ingestion (all files in single insert call)
- Incremental updates (skips already-processed documents)
- Timing reports
- Document status tracking
"""
import asyncio
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from config import get_rag_instance, WORKING_DIR, WORKSPACE, STORAGE_MODE

load_dotenv()


def compute_doc_hash(content: str) -> str:
    """
    Compute the same MD5 hash LightRAG uses for document deduplication.
    
    LightRAG identifies documents by: "doc-" + md5(content.strip())
    """
    return "doc-" + hashlib.md5(content.strip().encode()).hexdigest()


def get_ingested_doc_ids(working_dir: str, workspace: str = None) -> set[str]:
    """
    Get set of already-ingested document IDs from local storage.
    
    For local storage, doc_status is in {working_dir}/{workspace}/kv_store_doc_status.json
    For cloud storage, this would need to query the doc_status storage directly.
    """
    ws = workspace or WORKSPACE
    
    # Local storage uses workspace subdirectory
    if STORAGE_MODE == "local":
        doc_status_file = Path(working_dir) / ws / "kv_store_doc_status.json"
    else:
        # Cloud storage - doc_status is still local but at root level
        doc_status_file = Path(working_dir) / "kv_store_doc_status.json"
    
    if not doc_status_file.exists():
        return set()
    
    try:
        with open(doc_status_file, "r") as f:
            data = json.load(f)
        return set(data.keys())
    except Exception as e:
        print(f"  ⚠️  Could not read doc_status: {e}")
        return set()


def check_files_status(
    files: list[Path], 
    working_dir: str,
    workspace: str = None,
) -> tuple[list[dict], list[dict]]:
    """
    Check which files are new vs already ingested.
    
    Returns:
        (new_files, already_ingested) - each is a list of dicts with file info
    """
    existing_ids = get_ingested_doc_ids(working_dir, workspace)
    
    new_files = []
    already_ingested = []
    
    for f in files:
        content = f.read_text(encoding="utf-8")
        doc_id = compute_doc_hash(content)
        
        file_info = {
            "path": f,
            "name": f.name,
            "doc_id": doc_id,
            "size": len(content),
            "content": content,  # Keep content for new files
        }
        
        if doc_id in existing_ids:
            del file_info["content"]  # Don't keep content for skipped files
            already_ingested.append(file_info)
        else:
            new_files.append(file_info)
    
    return new_files, already_ingested


async def ingest_directory(
    rag,
    directory: str,
    pattern: str = "processed_*.md",
    force: bool = False,
    working_dir: str = None,
    workspace: str = None,
) -> dict:
    """
    Ingest all matching files from a directory.
    
    Args:
        rag: LightRAG instance
        directory: Path to directory containing files
        pattern: Glob pattern for files (default: processed_*.md)
        force: If True, skip duplicate checking and ingest all files
        working_dir: Working directory for status checks
        workspace: Workspace (thread_id) for data isolation
    
    Returns:
        dict with ingestion results
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    files = sorted(dir_path.glob(pattern))
    if not files:
        print(f"⚠️  No files matching '{pattern}' in {directory}")
        return {"status": "no_files", "total": 0}
    
    print(f"\n📂 Found {len(files)} files matching '{pattern}'")
    
    # Check for duplicates (unless force mode)
    if force:
        new_files = [{"path": f, "name": f.name, "content": f.read_text()} for f in files]
        already_ingested = []
    else:
        target_dir = working_dir or rag.working_dir
        target_workspace = workspace or WORKSPACE
        new_files, already_ingested = check_files_status(files, target_dir, target_workspace)
    
    # Report status
    if already_ingested:
        print(f"\n⏭️  Skipping {len(already_ingested)} already-ingested files:")
        for f in already_ingested:
            print(f"    • {f['name']} (ID: {f['doc_id'][:16]}...)")
    
    if not new_files:
        print(f"\n✅ All files already ingested. Nothing to do.")
        return {
            "status": "up_to_date",
            "total": len(files),
            "skipped": len(already_ingested),
            "ingested": 0
        }
    
    print(f"\n📥 Ingesting {len(new_files)} new files...")
    
    # Prepare batch data
    texts = []
    ids = []
    file_paths = []
    
    for f in new_files:
        texts.append(f["content"])
        ids.append(f["path"].stem)  # Use filename without extension as ID
        file_paths.append(str(f["path"]))
        print(f"    • {f['name']} ({f.get('size', len(f['content'])):,} chars)")
    
    # Batch insert with timing
    print(f"\n🚀 Starting batch ingestion...")
    start_time = time.time()
    
    await rag.ainsert(texts, ids=ids, file_paths=file_paths)
    
    elapsed = time.time() - start_time
    total_chars = sum(len(t) for t in texts)
    
    # Results
    print(f"\n✅ Ingestion complete!")
    print(f"    Files:      {len(new_files)}")
    print(f"    Characters: {total_chars:,}")
    print(f"    Time:       {elapsed:.1f}s")
    print(f"    Speed:      {total_chars/elapsed:,.0f} chars/sec")
    
    # Generate timing report
    report = generate_timing_report(
        new_files, already_ingested, elapsed, total_chars
    )
    
    return {
        "status": "success",
        "total": len(files),
        "skipped": len(already_ingested),
        "ingested": len(new_files),
        "elapsed_seconds": elapsed,
        "total_chars": total_chars,
        "report": report
    }


def generate_timing_report(
    ingested: list, 
    skipped: list, 
    elapsed: float, 
    total_chars: int
) -> str:
    """Generate a markdown timing report."""
    
    report = f"""# LightRAG Ingestion Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Files Ingested | {len(ingested)} |
| Files Skipped | {len(skipped)} |
| Total Characters | {total_chars:,} |
| Total Time | {elapsed:.1f}s |
| Processing Speed | {total_chars/elapsed:,.0f} chars/sec |

## Ingested Files

"""
    
    if ingested:
        for f in ingested:
            size = f.get('size', len(f.get('content', '')))
            report += f"- `{f['name']}` ({size:,} chars)\n"
    else:
        report += "_No new files ingested._\n"
    
    report += "\n## Skipped Files (Already Ingested)\n\n"
    
    if skipped:
        for f in skipped:
            report += f"- `{f['name']}` (ID: `{f['doc_id'][:16]}...`)\n"
    else:
        report += "_No files skipped._\n"
    
    return report


def save_timing_report(report: str, output_dir: str = None):
    """Save timing report to file."""
    output_path = Path(output_dir or "src/rag/time_it")
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find next report number
    existing = list(output_path.glob("timing_report_*.md"))
    next_num = len(existing) + 1
    
    report_file = output_path / f"timing_report_{next_num}.md"
    report_file.write_text(report)
    
    print(f"\n📄 Timing report saved: {report_file}")
    return report_file


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents into LightRAG")
    parser.add_argument(
        "--input", "-i", 
        default="src/rag/files_to_embed",
        help="Input directory containing files to ingest"
    )
    parser.add_argument(
        "--pattern", "-p",
        default="processed_*.md",
        help="Glob pattern for files (default: processed_*.md)"
    )
    parser.add_argument(
        "--db", "-d",
        default=None,
        help="Working directory for LightRAG database"
    )
    parser.add_argument(
        "--workspace", "-w",
        default=None,
        help="Workspace (thread_id) for data isolation"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-ingestion of all files (skip duplicate check)"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating timing report"
    )
    parser.add_argument(
        "--llm-backend", "-l",
        default=None,
        choices=["gemini", "qwen"],
        help="LLM backend to use (overrides config.py)"
    )
    
    args = parser.parse_args()
    
    # Initialize RAG
    rag = await get_rag_instance(
        working_dir=args.db, 
        workspace=args.workspace,
        llm_backend=args.llm_backend
    )
    
    try:
        # Run ingestion
        result = await ingest_directory(
            rag,
            directory=args.input,
            pattern=args.pattern,
            force=args.force,
            working_dir=args.db,
            workspace=args.workspace,
        )
        
        # Save timing report
        if not args.no_report and result.get("report"):
            save_timing_report(result["report"])
        
    finally:
        # Cleanup
        await rag.finalize_storages()
        print("\n👋 Done!")


if __name__ == "__main__":
    asyncio.run(main())