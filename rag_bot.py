from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
from langchain_openai.chat_models.azure import AzureChatOpenAI
import dotenv
import os
from function_libraries import create_rag_chain_with_score, format_rag_response_new_grouped
from langchain_community.vectorstores import AzureSearch

dotenv.load_dotenv()

def bot_model(text, indexname, chat_history):
    """
    Creates a RAG-based chatbot model using Azure OpenAI and Azure Cognitive Search.
    
    Args:
        text (str): The input text/question from the user
        indexname (str): The name of the Azure Search index to use
        chat_history (list): List of previous chat interactions
        
    Returns:
        tuple: (answer, references) where answer is the bot's response and references are the sources
    """
    # Get environment variables
    AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
    CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
    CDR_AZURE_COGNITIVE_SEARCH_API_KEY = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_API_KEY")
    
    print(
        f"1: {AZURE_API_KEY}",
        f"2: {AZURE_OPENAI_ENDPOINT}",
        f"3: {CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME}",
        f"4: {CDR_AZURE_COGNITIVE_SEARCH_API_KEY}"
    )

    # Initialize embedding model
    embedding = AzureOpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=AZURE_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2023-05-15"
    )
    
    # Initialize chat model
    model = AzureChatOpenAI(
        model="gpt-4o-mini-2024-07-18",
        azure_deployment="gpt-4o-mini",
        api_key=AZURE_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2023-03-15-preview"
    )
    
    # Set up Azure Cognitive Search
    vector_store_address = f"https://{CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME}.search.windows.net"
    vectorstore = AzureSearch(
        azure_search_endpoint=vector_store_address,
        azure_search_key=CDR_AZURE_COGNITIVE_SEARCH_API_KEY,
        index_name=indexname,
        embedding_function=embedding,
        search_type='semantic_hybrid'
    )
    
    def get_response(chain, question: str, chat_history: list = None):
        """Get response from the chain."""
        if chat_history is None:
            chat_history = []
        return chain.invoke({
            "question": question,
            "chat_history": chat_history
        })
    
    # Initialize and use the chain
    chain = create_rag_chain_with_score(
        vectorstore=vectorstore,
        llm_model=model
    )
    
    # Get and format response
    response = get_response(
        chain=chain,
        question=text,
        chat_history=chat_history
    )
    
    return format_rag_response_new_grouped(response)