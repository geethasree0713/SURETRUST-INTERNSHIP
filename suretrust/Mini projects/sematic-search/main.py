from pocketflow import Flow

from nodes import (
    ChunkDocumentsNode,
    EmbedDocumentsNode,
    CreateIndexNode,
    EmbedQueryNode,
    SearchNode
)


chunk_node = ChunkDocumentsNode()

embed_docs_node = EmbedDocumentsNode()

index_node = CreateIndexNode()

embed_query_node = EmbedQueryNode()

search_node = SearchNode()


chunk_node - "default" >> embed_docs_node

embed_docs_node - "default" >> index_node

offline_flow = Flow(start=chunk_node)


embed_query_node - "default" >> search_node

online_flow = Flow(start=embed_query_node)


with open(
    "data/sample.txt",
    "r",
    encoding="utf-8"
) as f:

    text = f.read()

shared = {
    "texts": [text]
}


print("\n========== INDEXING ==========")

offline_flow.run(shared)


query = input("\nEnter query: ")

shared["query"] = query


print("\n========== SEARCH ==========")

online_flow.run(shared)
# "How does meaning-based retrieval work?"
# "Semantic search retrieves information based on meaning instead of exact keyword matching."
