from function_libraries import *
from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
from langchain_openai.chat_models.azure  import AzureChatOpenAI
import dotenv, os

dotenv.load_dotenv()

def bot_model(text, indexname):
    
    AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")

    embedding = AzureOpenAIEmbeddings(
                        model="text-embedding-3-small",
                        api_key=AZURE_API_KEY,
                        azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
                        api_version="2023-05-15")

    model = AzureChatOpenAI(
                model="gpt-4o-mini-2024-07-18",
                azure_deployment="gpt-4o-mini",
                api_key=AZURE_API_KEY,
                azure_endpoint="https://ocr-chatbot-mccalla.openai.azure.com/",
                api_version="2023-03-15-preview"
            )

    chat_history =[]
    vectorstore = vector_store(embedding_model=embedding, index_name=indexname)
    response = retrieval_chain(text, vectorstore, model, chat_history)
    print(response)
    return response