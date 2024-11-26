import streamlit as st
from rag_bot import bot_model
from function_libraries import get_indexname

# Page config
st.set_page_config(
    page_title="Client Directive Chatbot",
    page_icon="🧊",
)

# Custom CSS with updated styling
st.markdown('''
<style>
/* General App Styling */
.stApp {
    background-color: #FAFAFA;
    color: #f0f2f6;
}

/* Textarea Styling */
[data-baseweb="textarea"] {
    color: #17202a;
}

/* Message Content Styling */
.message-content {
    max-width: 80%;
    padding: 20px;
    border-radius: 10px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 8px 0;
}

/* User and Bot Message Containers */
.user-message-container, .bot-message-container {
    display: flex;
    margin: 8px 0;
    width: 100%;
}

.user-message-container {
    justify-content: flex-end;
}

.bot-message-container {
    justify-content: flex-start;
}

/* User and Bot Message Styling */
.user-message {
    background-color: #ECEBEC;
    color: #000000;
    margin-left: 20%;
}

.assistant-message {
    background-color: #6B7DBA;
    color: #FFFFFF;
    margin-right: 20%;
}

/* Button Styling */
.stButton > button {
    background-color: #ffffff !important;
    color: black !important;
    border: 2px solid #6B7DBA !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.8rem !important;
    min-height: 0px !important;
    height: auto !important;
    line-height: 1.2 !important;
    margin: 4px 0 !important;
}

/* Reference Section Styling */
.reference-container {
    background-color: #ffffff;
    color: black;
    border: 2px solid #6B7DBA;
    padding: 12px;
    margin: 10px 0;
    border-radius: 4px;
    font-size: 0.9rem;
}

/* Key Points Section Styling */

/* Bold Text Styling */
.message-content strong {
    font-weight: 600;
}
</style>
''', unsafe_allow_html=True)


# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "show_references_per_message" not in st.session_state:
    st.session_state.show_references_per_message = {}

# Header
header_container = st.container()

# Left sidebar for client selection
with st.sidebar:
    st.write()
    search_query = st.chat_input("Search client...")
    
    options = [
        "Shellpoint Mortgage", "Nationstar Mortgage", "M&T Bank", "Fannie Mae", "Freddie Mac"
    ]
    #"Freedom Mortgage", "JP Morgan Chase Bank","Fay Servicing", "PHH Corporation", "Flagstar Bank", "Pennymac Loan Services", "US Bank"

    filtered_options = [option for option in options if search_query and search_query.lower() in option.lower()] if search_query else options

    with st.expander("Select a client"):
        selected_option = st.radio("Select an option:", filtered_options, label_visibility="collapsed")

    if selected_option:
        st.write("Retrieving Information From: ", f'\n :red[{selected_option}]')
        indexname = get_indexname(selected_option)

with header_container:
    # Display the image
    #st.image("ClientDirective.svg", width=300,use_container_width=True)  # Adjust the path and width as needed
    # Display the title
    st.markdown(f'<h1 style="text-align: center; color: black;">Client Directive Chatbot</h1>', unsafe_allow_html=True)
    st.info(f"**:red[✒️ The Chatbot is responding based on {selected_option}]** \n\n✒️ **:red[Client Directive Chatbot can make mistakes. Please double-check responses.]**")

def toggle_references(message_id):
    st.session_state.show_references_per_message[message_id] = not st.session_state.show_references_per_message.get(message_id, False)

import os

# Path to avatars (assuming they are in the same directory as your Streamlit script)
user_avatar_path = "user.png"
bot_avatar_path = "robot.png"

def format_message_content(content):
    """
    Format the message content with proper spacing and list formatting.
    Handles numbered lists and regular content differently.
    """
    # Check if content is a numbered list
    lines = content.strip().split('\n')
    
    def is_numbered_item(text):
        """Helper function to check if a line is a numbered item"""
        # Look for both plain numbers and numbers with dots
        text = text.strip()
        return any(text.startswith(f"{i}.") or text.startswith(f"{i} .") for i in range(1, 11))
    
    # Check if any line starts with a number followed by a period
    is_numbered_list = any(is_numbered_item(line) for line in lines)
    
    if is_numbered_list:
        formatted_items = []
        for line in lines:
            if line.strip():  # Only process non-empty lines
                # Remove any existing numbers at the start
                cleaned_line = ' '.join(line.strip().split()[1:])
                formatted_items.append(cleaned_line)
                
        return f"""
            <ol class="numbered-list" style="margin-top: 0px; margin-bottom: 0px;">
                {''.join(f'<li>{item}</li>' for item in formatted_items)}
            </ol>
        """
    else:
        # Handle non-list content with proper margins
        return f'<p style="margin: 8px 0px;">{content}</p>'
    
def display_message(role, content, message_id, references=None):
    """
    Display chat messages with proper formatting and reference handling.
    
    Args:
        role (str): 'user' or 'assistant'
        content (str): message content
        message_id (int): unique message identifier
        references (str, optional): reference content for assistant messages
    """
    with st.container():
        if role == "user":
            col1, col2 = st.columns([9, 1])
            with col1:
                st.markdown(f"""
                    <div class="user-message-container">
                        <div class="message-content user-message">{content}</div>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.image(user_avatar_path, width=40)
        else:
            col1, col2 = st.columns([1, 9])
            with col1:
                st.image(bot_avatar_path, width=40)
            with col2:
                # Display content directly for assistant's message
                st.markdown(f"""
                    <div class="bot-message-container">
                        <div class="message-content assistant-message">{content}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Handle references section
                if references:
                    ref_button = st.button(
                        "📑 References" if not st.session_state.show_references_per_message.get(message_id, False) 
                        else "❌ Hide",
                        key=f"ref_toggle_{message_id}",
                        use_container_width=False
                    )
                    
                    if ref_button:
                        toggle_references(message_id)
                    
                    if st.session_state.show_references_per_message.get(message_id, False):
                        st.markdown(f"""
                            <div class="reference-container">{references}</div>
                        """, unsafe_allow_html=True)

# Display chat history
for idx, message in enumerate(st.session_state.chat_history):
    display_message(
        message["role"], 
        message["content"], 
        idx,
        message.get("references") if message["role"] == "assistant" else None
    )

# Get user input
text = st.chat_input("Drop your question...")

# Handle messages and responses
if text:
    # Immediately append and display user message
    st.session_state.chat_history.append({"role": "user", "content": text})
    st.rerun()

if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
    last_user_message = st.session_state.chat_history[-1]["content"]
    
    # Get the bot's response
    bot_response = bot_model(last_user_message, indexname, st.session_state.chat_history)
    
    # Prepare the bot's answer and references
    bot_res = bot_response[0].replace("AI: ","").replace(": ","").replace("Assistant","").replace('\n\n','\n')
    import re
    bot_answer = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", bot_res)
    references = bot_response[1].replace(
        "@Tag4DateRetrieved@", "\n:red[Date Document Retrieved ]"
    ).replace(
        "@Tag4Source@", "\n\n\n:red[Source ]"
    ).replace(
        "@Tag4pagenum@", "\n\n\n:red[Page ]"
    ).replace(
        "@Tag4Citation@", "\n\n:red[Citation ]"
    ).replace(
        "Reference :","<b>Reference :<b>")

    # Append the bot's response to chat history
    message_id = len(st.session_state.chat_history)
    
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": bot_answer,
        "references": references
    })

    # Display the bot's response
    display_message("assistant", bot_answer, message_id, references)
