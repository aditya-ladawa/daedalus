"""
Query Script for LightRAG
"""
import asyncio
import time
from lightrag import QueryParam
from config import get_rag_instance

async def query(rag, question: str, mode: str = "hybrid") -> str:
    """
    Query the knowledge graph.
    
    Modes:
        - "hybrid": local + global combined (recommended)
        - "local": entity-focused (specific relationships)
        - "global": theme-focused (broad patterns)  
        - "naive": vector-only (no graph)
    """
    print(f"\n🔍 Querying ({mode}): {question}")
    start = time.time()
    
    result = await rag.aquery(question, param=QueryParam(mode=mode))
    
    elapsed = time.time() - start
    print(f"  ⏱️  Query time: {elapsed:.2f}s")
    
    return result

async def main():
    rag = await get_rag_instance(working_dir="./lightrag_data")
    
    print("\n💡 LightRAG Query Interface")
    print("Type 'exit' or 'quit' to stop.")
    
    while True:
        try:
            q = input("\n📝 Enter your question: ").strip()
            if not q:
                continue
            if q.lower() in ["exit", "quit"]:
                break
            
            # Check for mode commands
            mode = "hybrid"  # default
            
            if q.startswith("/"):
                parts = q.split(" ", 1)
                cmd = parts[0].lower()
                
                if cmd in ["/local", "/global", "/hybrid", "/naive", "/mix"]:
                    mode = cmd[1:] # remove slash
                    if mode == "mix": mode = "hybrid"
                    
                    if len(parts) > 1:
                        q = parts[1]
                    else:
                        print(f"⚠️  Mode set to {mode}, but no query provided.")
                        continue
                else:
                    print(f"ℹ️  Unknown command '{cmd}'. Using default hybrid mode.")
            
            answer = await query(rag, q, mode)
            print("\n" + "-"*40)
            print("🤖 Answer:")
            print(answer)
            print("-" * 40)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
