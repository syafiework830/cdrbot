import streamlit as st
#from styling import background
from rag_bot import bot_model
from function_libraries import get_indexname

st.set_page_config(
    page_title="Client Directive Chatbot",
    page_icon="👋",
)
header_container = st.container(border=True)
# Page Title
header_container.markdown(f'<h1 style="text-align: center; color: black;"> Client Directive Chatbot </h1>',unsafe_allow_html=True)

# Background set to gray
header_container.markdown(
    #background(),
        """
    <style>
    /* Change background color of the entire page */
    .stApp {
        background-color: #b3b6b7;
         color: #f0f2f6;  /* Light grey background */
    }

    /* Change font color inside chat input box */
    [data-baseweb="textarea"] {
        color: #17202a; /* Lime green font color */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar inputs
with st.sidebar:
    st.write()
    # Search input for filtering options
    search_query = st.chat_input("Search client...")
    
    # Sample list of radio button options
    options = [
        "Shellpoint Mortgage", "Nationstar Mortgage", "M&T Bank", "Freedom Mortgage", "JP Morgan Chase Bank",
        "Fay Servicing", "PHH Corporation", "Flagstar Bank", "Pennymac Loan Services", "US Bank"]

# Filter the options based on the search query (case-insensitive)
    filtered_options = [option for option in options if search_query.lower() in option.lower()] if search_query else options

# Use an expander to hide the options
    with st.expander("Select a client"):
    # Display the filtered options in a radio button within the expander
        selected_option = st.radio("Select an option:", filtered_options, label_visibility="collapsed")

# Show the selected option
    if selected_option:
        st.write("Retrieving Information From: ",'\n'f"{selected_option}")
        indexname = get_indexname(selected_option)

st.markdown(f'<div style="text-align: center"> You are interacting with {selected_option} </div>', unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history with avatars
import streamlit as st

# Initialize chat history if not present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    # Create a container for each message
    with st.container():
        if message["role"] == "user":
            # Create two columns to display the message and avatar
            col1, col2 = st.columns([1, 9])  # Narrow column for avatar, wide for text
            with col1:
                st.markdown('<div style="text-align: center;">👨</div>', unsafe_allow_html=True)  # Centered user avatar
            with col2:
                st.markdown(f"<div style='padding: 10px; background-color: #5dade2; border-radius: 10px; color: ##e8f4f8;'>"
                             f"{message['content']}</div>", unsafe_allow_html=True)  # User message with background and padding
        else:
            # Bot message with avatar on the right
            col1, col2 = st.columns([9, 1])  # Wide column for text, narrow for avatar
            with col1:
                st.markdown(f"<div style='padding: 10px; background-color: #7d3c98; border-radius: 10px; color: ##e8f4f8;'>"
                             f" {message['content']} </div>", unsafe_allow_html=True)  # Bot message with background and padding
            with col2:
                st.markdown('<div style="text-align: center;">🤖</div>', unsafe_allow_html=True)  # Centered bot avatar

# Get user input
text = st.chat_input("Drop your question...")

# Only proceed if the user provides input
if text:
    print(indexname)
    bot_response = bot_model(text, indexname)

    # Append user message to the chat history
    st.session_state.chat_history.append({"role": "user", "content": text})

    # Display user message (on the right)
    with st.container():
        col1, col2 = st.columns([1, 9])  # Narrow column for avatar, wide for text
        with col1:
            st.markdown('<div style="text-align: center;">👨</div>', unsafe_allow_html=True)  # Centered user avatar
        with col2:
            st.markdown(f"<div style='padding: 10px; background-color: #5dade2; border-radius: 10px;'>{text}</div>", unsafe_allow_html=True)  # User message with background and padding

    # Simulate bot response and add it to the chat history (for demonstration purposes)

    st.session_state.chat_history.append({"role": "bot", "content": bot_response})

    # Display bot message (on the left)
    with st.container():
        col1, col2 = st.columns([9, 1])  # Wide column for text, narrow for avatar
        with col1:
            st.markdown(f"<div style='padding: 10px; background-color: #7d3c98; border-radius: 10px;'> {bot_response} </div>", unsafe_allow_html=True)  # Bot message with background and padding
        with col2:
            st.markdown('<div style="text-align: center;">🤖</div>', unsafe_allow_html=True)  # Centered bot avatar


    # Generate the bot response using the bot_model
   

    ## Append the bot response to the chat history
    #st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
#
    #    # Display bot message (on the left)
    #col1, col2 = st.columns([1, 2])
    #with col1:
    #    st.markdown('🤖')  # Bot avatar
    #with col2:
    #    st.markdown(f"{bot_response}") 