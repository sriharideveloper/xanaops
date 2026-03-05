import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

print("Loading the paired dataset...")
df = pd.read_csv("paired_chats.csv")

print("Initializing ChromaDB (Creating 'xana_memory_db')...")
chroma_client = chromadb.PersistentClient(path="./xana_memory_db")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Create or open the memory collection
collection = chroma_client.get_or_create_collection(name="xana_memories", embedding_function=sentence_transformer_ef)

documents = df['Message'].astype(str).tolist()
metadatas = [{"title": str(t), "date": str(d)} for t, d in zip(df['Chat Title'], df['Date'])]
ids = [str(i) for i in range(len(documents))]

print(f"Embedding {len(documents)} paired memories...")

batch_size = 500
for i in range(0, len(documents), batch_size):
    end_idx = min(i + batch_size, len(documents))
    print(f"Processing batch {i} to {end_idx}...")
    collection.add(
        documents=documents[i:end_idx],
        metadatas=metadatas[i:end_idx],
        ids=ids[i:end_idx]
    )

print("Brain building complete! Your memory database is ready.")