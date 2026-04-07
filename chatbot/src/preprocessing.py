import os
from  langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import uuid

from utils import dispatcher
from ollama_client import ollama_client
from config import MODEL_EMBED, SIM_THRESHOLD


client_db = chromadb.EphemeralClient()
session_collections: dict[str, object] = {}


def get_collection(session_id):
    collection = client_db.get_or_create_collection(name=f'session_{session_id}', metadata={"hnsw:space": "cosine"})
    session_collections[session_id] = collection
    return collection


def load_docs(file):
    processed_file = dispatcher(file)
    if processed_file is None:
        raise ValueError(f'Unsupported file format: {file}')
    print('file loaded')
    return processed_file


def split_docs(docs):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=50, chunk_overlap=10
    )
    doc_splits = text_splitter.split_text(docs)
    print('doc splitted')
    return doc_splits


def ingest_documents(file, session_id='session-custom-134143413'):
    embeddings = []
    ids = []
    docs = []
    metadatas = []
    documents = load_docs(file)
    documents_ = split_docs(documents)
    collection = get_collection(session_id)
    for doc in documents_:
        response = ollama_client.embed(model=MODEL_EMBED, input=doc)
        embed = response["embeddings"]
        if embed:
            embeddings.append(embed[0])
            ids.append(str(uuid.uuid4()))
            docs.append(doc)
            metadatas.append({'session_id': session_id})
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=docs,
        metadatas=metadatas
    )
    print('added to the collection')
    return len(docs)


def retrieve_context(prompt, session_id, n_results=3):
    embed_prompt = ollama_client.embed(
        model=MODEL_EMBED,
        input=prompt
    )
    if session_id not in session_collections: return []
    collection = get_collection(session_id)
    if collection.count() == 0: return []
      
#    retrieved_context = collection.get(where={'session_id': session_id}, limit=1)
    results = collection.query(
        query_embeddings=[embed_prompt["embeddings"][0]],
        n_results=n_results,
        where={"session_id": session_id},
        include=["documents", "embeddings", "distances"]
    )

    doc = results["documents"][0]
    distance = results["distances"][0]
    
    print(distance)
    # ilters against threshold to keep relevant docs only
    filtered_docs = [
        doc for doc, dist in zip(doc, distance) if dist < SIM_THRESHOLD
    ]
    print(filtered_docs)
    return filtered_docs


def purge_session(session_id):
    if session_id in session_collections:
        client_db.delete_collection(f'session_{session_id}')
        del session_collections[session_id]