from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os, dotenv
from langchain_community.vectorstores import AzureSearch
from typing import List
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import Document
from langchain.output_parsers.openai_tools import JsonOutputKeyToolsParser
from operator import itemgetter
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain.schema.output_parser import StrOutputParser

dotenv.load_dotenv()

AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
CDR_AZURE_COGNITIVE_SEARCH_INDEX_NAME = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_INDEX_NAME")
CDR_AZURE_COGNITIVE_SEARCH_API_KEY = os.environ.get("CDR_AZURE_COGNITIVE_SEARCH_API_KEY")
AZURE_CONN_STRING = os.environ.get("AZURE_CONN_STRING")
SQL_CONTAINER_NAME = os.environ.get("SQL_CONTAINER_NAME")

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import Document

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
        case "M&T Bank":
            return "cdr-mtbank"
        case _:
            return "Please choose a valid client!"


# Define the cited answer model
class cited_answer(BaseModel):
    """Answer the user question based only on the given sources, and cite the sources used."""
    answer: str = Field(
        ...,
        description="The answer to the user question, which is based only on the given sources.",
    )
    citations: List[int] = Field(
        ...,
        description="The integer IDs of the SPECIFIC sources which justify the answer.",
    )
    
def format_rag_response_new_grouped(response):
    """
    Format RAG response with answer and multiple citations in a readable format.
    Ensures proper spacing for bullet points and numbered lists.
    """
    output = response['output']
    formatted_citations = ""
    
    if 'cited_answer' in output:
        # Format the answer to ensure proper bullet point spacing
        answer = output['cited_answer']['answer']
        # Add extra newline before and after bullet points and numbered lists
        answer = (answer.replace("\n•", "\n\n•")
                      .replace("\n▪", "\n\n▪")
                      .replace("\n-", "\n\n-")
                      .replace("\n1.", "\n\n1.")
                      .replace("\n2.", "\n\n2.")
                      .replace("\n3.", "\n\n3.")
                      .replace("\n4.", "\n\n4.")
                      .replace("\n5.", "\n\n5.")
                      .replace("\n6.", "\n\n6.")
                      .replace("\n7.", "\n\n7.")
                      .replace("\n8.", "\n\n8.")
                      .replace("\n9.", "\n\n9.")
                      .replace("\n10.", "\n\n10."))
        
        citations = output['cited_answer']['citations']
        docs = output['docs']

        if citations and len(citations) > 0:
            for idx, citation_idx in enumerate(citations):
                if citation_idx < len(docs):
                    doc = docs[citation_idx]
                    # Format citation content with proper bullet point spacing
                    citation = (doc.page_content.replace('\n', ' ')
                                              .strip()
                                              .replace("•", "\n\n•")
                                              .replace("▪", "\n\n▪")
                                              .replace("-", "\n\n-"))
                    
                    source_snippet = doc.metadata.get('source', 'Unknown source')
                    date_retrieved = source_snippet.split(" - ")[0].replace("_","/")
                    source = source_snippet.split(" - ")[1]
                    page = doc.metadata.get('pageNum', 'Unknown page')
                    similarity_score = doc.metadata.get('similarity_score', None)
                    score_display = f" (Similarity: {similarity_score:.2%})" if similarity_score is not None else ""

                    formatted_citations += f"\n📌 <span style='background-color:#f7dc6f; color:black; padding:3px;'><b>Reference {idx + 1}{score_display}</b></span> \n"
                    formatted_citations += f"@Tag4DateRetrieved@: {date_retrieved}\n"
                    formatted_citations += f"@Tag4Source@: {source}\n"
                    formatted_citations += f"@Tag4pagenum@: {page}\n"
                    formatted_citations += f"@Tag4Citation@: {citation}\n\n"
                    formatted_citations += "="*75 
                    formatted_citations += "\n\n"
            
            return answer, formatted_citations.strip()
        
        return answer, formatted_citations
    else:
        # Format simple answers with proper bullet point spacing
        answer = output['answer']
        answer = (answer.replace("\n•", "\n\n•")
                      .replace("\n▪", "\n\n▪")
                      .replace("\n-", "\n\n-")
                      .replace("\n1.", "\n\n1.")
                      .replace("\n2.", "\n\n2.")
                      .replace("\n3.", "\n\n3.")
                      .replace("\n4.", "\n\n4.")
                      .replace("\n5.", "\n\n5.")
                      .replace("\n6.", "\n\n6.")
                      .replace("\n7.", "\n\n7.")
                      .replace("\n8.", "\n\n8.")
                      .replace("\n9.", "\n\n9.")
                      .replace("\n10.", "\n\n10."))
        return answer, formatted_citations

def create_rag_chain_with_score(vectorstore, llm_model):
    """
    Create a RAG chain with chat history and dynamic citations based on similarity score threshold.
    Citations are automatically included only when similarity score >= 0.65
    """
    
    # Simple query detection prompt
    simple_query_prompt = ChatPromptTemplate.from_messages([
        ("system", """Determine if this is a simple query that doesn't require document lookup.
        Simple queries include:
        - Greetings (hi, hello, hey)
        - Basic math (1+1, 2*3)
        - Simple chitchat
        Return only "true" for simple queries or "false" for queries needing document lookup."""),
        ("human", "{question}")
    ])
    
    # Initialize the LLM with citation tool
    llm_with_tools = llm_model.bind_tools(
        [cited_answer],
        tool_choice="cited_answer",
    )
    output_parser = JsonOutputKeyToolsParser(key_name="cited_answer", first_tool_only=True)
    
    # Create prompts
    base_prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question based on the following context: {context}. If the answer has bullet points or numbering points, please distinguish each on a new line.Example: 1.<content> 2.<content> or in this '-','▪','•' "),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    simple_response_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    retriever_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    def format_docs(docs: List[Document]) -> str:
        """Format documents into a simple string."""
        return "\n\n".join([doc.page_content for doc in docs])
    
    def format_docs_with_id(docs: List[Document]) -> str:
        """Format documents with source IDs and metadata."""
        formatted = [
            f"Source ID: {i}\nArticle Title: {doc.metadata.get('title', 'No title')}\nArticle Snippet: {doc.page_content}"
            for i, doc in enumerate(docs)
        ]
        return "\n\n" + "\n\n".join(formatted)
    
    def retrieve_with_history(input_dict):
        """Retrieve documents considering chat history and similarity scores."""
        llm_response = llm_model.invoke(
            retriever_prompt.format(
                question=input_dict["question"],
                chat_history=input_dict["chat_history"]
            )
        )
        
        # Get documents with similarity scores
        docs_with_scores = vectorstore.similarity_search_with_relevance_scores(llm_response.content)
        
        # Filter and process documents
        filtered_docs = []
        max_similarity = 0.0
        
        for doc, score in docs_with_scores:
            doc.metadata['similarity_score'] = score
            filtered_docs.append(doc)
            max_similarity = max(max_similarity, score)
        
        print("Retrieved docs count:", len(filtered_docs))
        [print(f"Score: {doc.metadata['similarity_score']:.2%}") for doc in filtered_docs]
        
        return filtered_docs, max_similarity >= 0.65  # Return docs and whether max similarity meets threshold
    
    def handle_simple_query(input_dict):
        """Handle simple queries and complex queries with dynamic citation inclusion."""
        is_simple = llm_model.invoke(
            simple_query_prompt.format(question=input_dict["question"])
        ).content.strip().lower() == "true"
        
        if is_simple:
            # For simple queries, return direct response without citations
            response = llm_model.invoke(
                simple_response_prompt.format(
                    question=input_dict["question"],
                    chat_history=input_dict["chat_history"]
                )
            )
            return {
                "cited_answer": {
                    "answer": response.content,
                    "citations": []
                },
                "docs": []
            }
        
        # For complex queries, check similarity scores
        docs, should_include_citations = retrieve_with_history(input_dict)
        
        # If any document has similarity >= 0.7, include citations
        if should_include_citations:
            context = format_docs_with_id(docs)
            response = llm_with_tools.invoke(
                base_prompt.format(
                    context=context,
                    question=input_dict["question"],
                    chat_history=input_dict["chat_history"]
                )
            )
            parsed_response = output_parser.invoke(response)
            return {
                "cited_answer": parsed_response,
                "docs": docs
            }
        else:
            # For low similarity scores, don't include citations
            context = format_docs(docs) if docs else ""
            response = llm_model.invoke(
                base_prompt.format(
                    context=context,
                    question=input_dict["question"],
                    chat_history=input_dict["chat_history"]
                )
            )
            return {
                "answer": response.content,
                "docs": docs
            }
    
    # Build the main chain
    chain = RunnableParallel(
        {
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history")
        }
    ).assign(
        output=RunnableLambda(handle_simple_query)
    ).pick(["output"])
    
    return chain