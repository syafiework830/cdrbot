from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os, dotenv
from langchain_community.vectorstores import AzureSearch

dotenv.load_dotenv()

AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
CDR_AZURE_COGNITIVE_SEARCH_INDEX_NAME = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_INDEX_NAME")
CDR_AZURE_COGNITIVE_SEARCH_API_KEY = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_API_KEY")
AZURE_CONN_STRING = os.environ.get("AZURE_CONN_STRING")
SQL_CONTAINER_NAME = os.environ.get("SQL_CONTAINER_NAME")

def vector_store(embedding_model, index_name:str):
    vector_store_address = f"https://{CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME}.search.windows.net"

    vectorstore: AzureSearch = AzureSearch(
        azure_search_endpoint=vector_store_address,
        azure_search_key=CDR_AZURE_COGNITIVE_SEARCH_API_KEY,
        index_name = index_name,
        embedding_function= embedding_model,
        search_type='similarity' # default value = Hybrid
    )

    return vectorstore


def vectorize(document_path, vectorstore:any, chunk_size:int, chunk_overlap: int) -> any:
    document = PyPDFLoader(document_path).load()

    text_splitter = RecursiveCharacterTextSplitter(
        separators=['.'],
        chunk_size = chunk_size,
        chunk_overlap  = chunk_overlap,
        length_function = len,
    )

    docs = text_splitter.split_documents(document)

    return vectorstore.add_documents(documents=docs)

from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import MessagesPlaceholder

def retrieval_chain(text, vector_store, llm_model,chat_history):

    prompt = ChatPromptTemplate.from_messages([
            ("system", "answer the question briefly {context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", '{input}')
        ])

    retriever_prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", '{input}')
        ])

    chain = create_stuff_documents_chain(llm_model, prompt)

    retriever = vector_store.as_retriever() #search_kwargs={"score_threshold": 0.5, "k" : 2})
   

    history_aware_retriever = create_history_aware_retriever(
            llm=llm_model,
            retriever=retriever,
            prompt=retriever_prompt,
        )

    retrieval_chain = create_retrieval_chain(
            history_aware_retriever,
            chain
        )

    response = retrieval_chain.invoke({
            "input": text,
            "context": "cdr",
            "chat_history":chat_history
        })

    return response['answer']

from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
from langchain.schema import Document

def batch_vectorize(vector_store:AzureSearch, folderpath: any, unwanted: set):
    '''File naming convention: MM_dd_YYYY'''

    docs = []
    date_data = []
    path = os.listdir(folderpath)
    print("Path:", path)

    for file in path:
        # Only process if file is a PDF and not in unwanted set
        if file.endswith(".pdf") and file not in unwanted:
            docs.append(file)
            print(file)
            date_data.append(file.split(' - ')[0])  # Extract date portion

    for file in docs:
        date = file.split(' - ')[0]
        doc = PyPDFLoader(os.path.join(folderpath,file)).load()
        print(f"Vectorizing {doc}")
        splitter = RecursiveCharacterTextSplitter(separators= '\n', keep_separator= True, chunk_size = 250, chunk_overlap = 50)
        chunked_docs = []
        for document in doc:
            # Split the page content text into chunks
            chunks = splitter.split_text(document.page_content)
            chunked_docs.extend(chunks)

            doc_object = [Document(page_content=chunks,
                                metadata= {'date': date, 'source' : file, 'file_id' : f"{file}-{i}"})
                                for i, chunks in enumerate(chunked_docs)]
            try:
                vector_store.add_documents(documents=doc_object)
            except ValueError:
                print(f"{ValueError}")
    
    return print("Documents successfully vectorized!")


def sort_similarity_results_by_date(results, reverse=True):
    """
    Sort similarity search results by date in metadata
    
    Parameters:
    results (list): List of (Document, score) tuples from similarity_search_with_relevance_scores
    reverse (bool): If True, sort in descending order; if False, ascending order
    
    Returns:
    list: Sorted list of (Document, score) tuples
    """
    def parse_date(date_str):
        # Convert date string (e.g., "22_10") to a comparable format
        month, day = map(int, date_str.split('_'))
        # Assuming all dates are in 2024, adjust as needed
        return f"2024-{month:02d}-{day:02d}"
    
    # Sort the results based on the date in metadata
    sorted_results = sorted(
        results,
        key=lambda x: parse_date(x[0].metadata['date']),
        reverse=reverse
    )
    
    return sorted_results

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

def rephrase_page_content(text:str, llm_model:any, store:dict, chat_history: list, page_content: str, session_id:str):
    prompt = ChatPromptTemplate.from_messages([
            ("system", "Rephrase {page_content} to answer {input}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "Answer {input} based on {page_content}")
        ])

    chain = prompt | llm_model

    def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]

    chain_with_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    chat_history.append(text)

    response = chain_with_history.invoke(
            {"input": text, "history": chat_history, "page_content": page_content},
            config={"configurable": {"session_id": session_id}}
        )
    
    return response.content

def get_indexname(client):
    match client:
        case "Shellpoint Mortgage":
            return "cdr-shellpoint"
        case "Nationstar Mortgage":
            return "cdr-nationstar"
        case _:
            return "Please choose a valid client!"