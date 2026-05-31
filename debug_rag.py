from rag import embed_text, supabase

vector = embed_text("Tell me about Sadhvi")
vector_str = "[" + ",".join(str(x) for x in vector) + "]"
print("Format check:", vector_str[:80])
print("Vector length:", len(vector))

result = supabase.rpc("match_documents", {
    "query_embedding": vector_str,
    "match_count": 3,
    "similarity_threshold": 0.0
}).execute()

print("RPC result:", result.data)
