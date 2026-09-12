from pocketflow import Node, BatchNode
import numpy as np
import faiss

from utils import (
    get_embedding,
    fixed_size_chunk
)


class ChunkDocumentsNode(BatchNode):

    def prep(self, shared):

        return shared["texts"]

    def exec(self, text):

        return fixed_size_chunk(text)

    def post(self, shared, prep_res, exec_res_list):

        all_chunks = []

        for chunks in exec_res_list:
            all_chunks.extend(chunks)

        shared["texts"] = all_chunks

        print(f"✅ Created {len(all_chunks)} chunks")

        return "default"



class EmbedDocumentsNode(BatchNode):

    def prep(self, shared):

        return shared["texts"]

    def exec(self, text):

        return get_embedding(text)

    def post(self, shared, prep_res, exec_res_list):

        embeddings = np.array(
            exec_res_list,
            dtype=np.float32
        )

        shared["embeddings"] = embeddings

        print("✅ Document embeddings created")

        return "default"


class CreateIndexNode(Node):

    def prep(self, shared):

        return shared["embeddings"]

    def exec(self, embeddings):

        dimension = embeddings.shape[1]

        index = faiss.IndexFlatL2(dimension)

        index.add(embeddings)

        return index

    def post(self, shared, prep_res, exec_res):

        shared["index"] = exec_res

        print("✅ FAISS index created")

        return "default"



class EmbedQueryNode(Node):

    def prep(self, shared):

        return shared["query"]

    def exec(self, query):

        query_embedding = get_embedding(query)

        return np.array(
            [query_embedding],
            dtype=np.float32
        )

    def post(self, shared, prep_res, exec_res):

        shared["query_embedding"] = exec_res

        return "default"



class SearchNode(Node):

    def prep(self, shared):

        return (
            shared["query_embedding"],
            shared["index"],
            shared["texts"]
        )

    def exec(self, inputs):

        query_embedding, index, texts = inputs

        distances, indices = index.search(
            query_embedding,
            k=1
        )

        best_index = indices[0][0]

        best_text = texts[best_index]

        distance = distances[0][0]

        return {
            "text": best_text,
            "distance": distance
        }

    def post(self, shared, prep_res, exec_res):

        print("\n🔍 Most Similar Text:")
        print(exec_res["text"])

        print(f"\n📏 Distance: {exec_res['distance']}")

        return "default"