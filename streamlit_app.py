#!/usr/bin/env python3
"""
ChatMMA v2.0 - Streamlit Web Interface
Deployed at: chatmma.streamlit.app
"""
import os
import sys
import streamlit as st
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

try:
    from chatbot import ChatMMA
    from query_optimizer import QueryOptimizer
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Make sure all dependencies are installed: pip install -r requirements.txt")
    st.stop()

# Page config
st.set_page_config(
    page_title="ChatMMA - AI MMA Analyst Consensus",
    page_icon="🥊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .tagline {
        text-align: center;
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .cost-badge {
        background-color: #f0f2f6;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-size: 0.9rem;
        color: #555;
    }
    .stChatMessage {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

# Initialize chatbot
@st.cache_resource
def init_chatbot():
    """Initialize ChatMMA instance (cached)."""
    # Try Streamlit secrets first, then environment variable
    api_key = None

    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except (FileNotFoundError, KeyError):
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        return None

    try:
        return ChatMMA(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing chatbot: {e}")
        return None

# Header
st.markdown('<div class="main-header">🥊 ChatMMA</div>', unsafe_allow_html=True)
st.markdown('<div class="tagline">"ChatMMA knows who every public analyst picked. AMA!"</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About ChatMMA v2.0")

    st.markdown("""
    ChatMMA synthesizes predictions from MMA analysts to give you:
    - **Consensus picks** for upcoming fights
    - **Context tags** explaining key factors
    - **Reasoning** behind each prediction
    - **Historical accuracy** of analysts

    ### Features
    - ✅ Cost-optimized queries ($0.001 each)
    - ✅ Analyst anonymity before events
    - ✅ Historical accuracy tracking
    - ✅ Context-rich answers
    """)

    st.divider()

    # Stats
    st.subheader("Session Stats")
    st.metric("Queries", st.session_state.query_count)
    st.metric("Total Cost", f"${st.session_state.total_cost:.4f}")

    if st.session_state.query_count > 0:
        avg_cost = st.session_state.total_cost / st.session_state.query_count
        st.metric("Avg Cost/Query", f"${avg_cost:.4f}")

    st.divider()

    # Database info
    if os.path.exists("data/chatmma.db"):
        st.success("✅ Database connected")

        # Get database stats
        try:
            optimizer = QueryOptimizer()
            import sqlite3
            conn = sqlite3.connect("data/chatmma.db")
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM predictions")
            prediction_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM analysts")
            analyst_count = cursor.fetchone()[0]

            conn.close()

            st.info(f"""
            **Database Stats:**
            - Events: {event_count}
            - Predictions: {prediction_count}
            - Analysts: {analyst_count}
            """)
        except Exception as e:
            st.warning(f"Could not load DB stats: {e}")
    else:
        st.warning("⚠️ Database not found. Run `python scripts/init_db.py`")

    st.divider()

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Main chat interface
st.subheader("Ask me anything about MMA predictions")

# Example questions
if not st.session_state.messages:
    st.info("💡 **Try asking:**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🥊 Who will win Kape vs Royval?"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Who will win between Kape and Royval?"
            })
            st.rerun()

        if st.button("📊 What are the consensus picks?"):
            st.session_state.messages.append({
                "role": "user",
                "content": "What are the consensus picks for the main card?"
            })
            st.rerun()

    with col2:
        if st.button("🎯 Why do analysts favor Kape?"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Why do analysts favor Kape over Royval?"
            })
            st.rerun()

        if st.button("📈 Which analysts are most accurate?"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Which analysts have the best historical accuracy?"
            })
            st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show metadata if available
        if "metadata" in message and message["role"] == "assistant":
            metadata = message["metadata"]
            if "cost_estimate" in metadata:
                cost = metadata["cost_estimate"]
                st.caption(f"💰 Query cost: ${cost['cost_usd']:.4f} ({cost['total_tokens']} tokens)")

# Chat input
if prompt := st.chat_input("Ask about any fight or event..."):
    # Check if chatbot is initialized
    chatbot = init_chatbot()

    if not chatbot:
        st.error("❌ ChatMMA not initialized. Please set ANTHROPIC_API_KEY environment variable.")
        st.stop()

    # Check if database exists
    if not os.path.exists("data/chatmma.db"):
        st.error("❌ Database not found. Please run `python scripts/init_db.py` first.")
        st.stop()

    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Analyzing predictions..."):
            try:
                result = chatbot.answer_question(prompt)

                # Display answer
                st.markdown(result["answer"])

                # Display cost info
                if "cost_estimate" in result.get("metadata", {}):
                    cost = result["metadata"]["cost_estimate"]
                    st.caption(f"💰 Query cost: ${cost['cost_usd']:.4f} ({cost['total_tokens']} tokens)")

                    # Update session stats
                    st.session_state.total_cost += cost['cost_usd']
                    st.session_state.query_count += 1

                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "metadata": result.get("metadata", {})
                })

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.divider()
st.caption("ChatMMA v2.0 - Built with Claude 4 and Streamlit | Cost-optimized architecture: $0.001/query")
