"""
ChatMMA Streamlit Web Interface
Easy-to-use web UI for MMA predictions analysis
"""
import streamlit as st
import sys
import os
sys.path.append('scripts')

import sqlite3
from anthropic import Anthropic
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="ChatMMA - MMA Predictions Analysis",
    page_icon="🥊",
    layout="wide"
)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Check for API key in environment or secrets
def get_api_key():
    # Try Streamlit secrets first (for deployment)
    try:
        return st.secrets["CLAUDE_API_KEY"]
    except:
        pass

    # Try environment variable
    if os.getenv("CLAUDE_API_KEY"):
        return os.getenv("CLAUDE_API_KEY")

    # Try config.yaml
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config['claude_api']['key']
    except:
        pass

    return None

def init_database_if_needed():
    """Initialize database if it doesn't exist"""
    db_path = "data/chatmma.db"

    if os.path.exists(db_path):
        return True

    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create all tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            date DATE NOT NULL,
            location TEXT,
            fights_count INTEGER,
            results_entered BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            fighter_a TEXT NOT NULL,
            fighter_b TEXT NOT NULL,
            weight_class TEXT,
            is_main_card BOOLEAN DEFAULT 0,
            scheduled_rounds INTEGER,
            result TEXT,
            method TEXT,
            round INTEGER,
            time TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            publication TEXT,
            analyst TEXT,
            url TEXT,
            credibility_score REAL DEFAULT 50.0,
            total_predictions INTEGER DEFAULT 0,
            correct_predictions INTEGER DEFAULT 0,
            accuracy_rate REAL DEFAULT 0.0
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fight_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            prediction TEXT NOT NULL,
            method TEXT,
            analyst_confidence TEXT,
            extraction_confidence REAL,
            reasoning TEXT,
            dfs_note TEXT,
            qa_status TEXT DEFAULT 'pending',
            raw_output_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fight_id) REFERENCES fights(id),
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fighter_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fighter_name TEXT NOT NULL UNIQUE,
            total_mentions INTEGER DEFAULT 0,
            traits TEXT,
            styles TEXT,
            strengths TEXT,
            weaknesses TEXT,
            dfs_notes TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            cost_usd REAL,
            operation TEXT
        )
        ''')

        conn.commit()
        conn.close()

        # Load initial data from YAML files
        try:
            from utils import load_yaml
            import yaml

            # Load events and fights
            if os.path.exists('fights.yaml'):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                with open('fights.yaml', 'r') as f:
                    fights_data = yaml.safe_load(f)

                for event in fights_data.get('events', []):
                    cursor.execute('''
                        INSERT OR IGNORE INTO events (name, date, location, fights_count)
                        VALUES (?, ?, ?, ?)
                    ''', (event['name'], event['date'], event['location'], len(event['fights'])))

                    cursor.execute('SELECT id FROM events WHERE name = ?', (event['name'],))
                    event_id = cursor.fetchone()[0]

                    for fight in event['fights']:
                        cursor.execute('''
                            INSERT OR IGNORE INTO fights
                            (event_id, fighter_a, fighter_b, weight_class, is_main_card,
                             scheduled_rounds, result, method, round, time)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            event_id,
                            fight['fighter_a'],
                            fight['fighter_b'],
                            fight['weight_class'],
                            fight.get('is_main_card', False),
                            fight.get('scheduled_rounds', 3),
                            fight.get('result'),
                            fight.get('method'),
                            fight.get('round'),
                            fight.get('time')
                        ))

                conn.commit()
                conn.close()

            # Load sources
            if os.path.exists('sources.yaml'):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                with open('sources.yaml', 'r') as f:
                    sources_data = yaml.safe_load(f)

                for source in sources_data.get('sources', []):
                    cursor.execute('''
                        INSERT OR IGNORE INTO sources (name, type, publication, analyst, url)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        source['name'],
                        source['type'],
                        source.get('publication', ''),
                        source.get('analyst', ''),
                        source['url']
                    ))

                conn.commit()
                conn.close()
        except Exception as e:
            st.warning(f"Database created but couldn't load initial data: {e}")

        return True

    except Exception as e:
        st.error(f"Error initializing database: {e}")
        return False

def get_database_connection():
    """Get database connection"""
    if not init_database_if_needed():
        return None

    db_path = "data/chatmma.db"
    return sqlite3.connect(db_path)

def chat_query(user_query, api_key):
    """Process chat query with Claude"""
    conn = get_database_connection()
    if not conn:
        return "Error: Database not available"

    cursor = conn.cursor()

    # Get relevant context
    query_lower = user_query.lower()

    # Find mentioned events
    cursor.execute('SELECT name, date FROM events ORDER BY date DESC LIMIT 10')
    events = cursor.fetchall()

    event_name = None
    for name, date in events:
        if name.lower() in query_lower:
            event_name = name
            break

    context_parts = []

    if event_name:
        # Get fights and predictions
        cursor.execute('''
            SELECT f.id, f.fighter_a, f.fighter_b, f.weight_class, f.result, f.method
            FROM fights f
            JOIN events e ON f.event_id = e.id
            WHERE e.name = ?
        ''', (event_name,))
        fights = cursor.fetchall()

        context_parts.append(f"EVENT: {event_name}\n")

        for fight_id, fa, fb, wc, result, method in fights:
            context_parts.append(f"\n{fa} vs {fb} ({wc})")

            if result:
                context_parts.append(f"  Result: {result} by {method}")

            # Get predictions
            cursor.execute('''
                SELECT s.analyst, s.accuracy_rate, p.prediction, p.method,
                       p.reasoning, p.analyst_confidence
                FROM predictions p
                JOIN sources s ON p.source_id = s.id
                WHERE p.fight_id = ? AND p.qa_status = 'approved'
            ''', (fight_id,))
            predictions = cursor.fetchall()

            if predictions:
                context_parts.append("  Predictions:")
                for analyst, acc, pred, method, reasoning, conf in predictions:
                    pick_name = fa if pred == 'fighter_a' else fb
                    context_parts.append(f"    - {analyst} ({acc:.1f}%): {pick_name}" +
                                       (f" by {method}" if method else ""))

    # Get top analysts
    cursor.execute('''
        SELECT analyst, accuracy_rate, total_predictions
        FROM sources
        WHERE total_predictions > 0
        ORDER BY accuracy_rate DESC
        LIMIT 5
    ''')
    top_analysts = cursor.fetchall()

    if top_analysts:
        context_parts.append("\n\nTOP ANALYSTS:")
        for analyst, acc, total in top_analysts:
            context_parts.append(f"  - {analyst}: {acc:.1f}% ({total} predictions)")

    context = "\n".join(context_parts)
    conn.close()

    # Call Claude
    try:
        client = Anthropic(api_key=api_key)

        system_prompt = """You are ChatMMA, an AI assistant that helps users understand MMA predictions by synthesizing insights from multiple expert analysts.

Provide consensus picks weighted by analyst credibility, explain reasoning, and highlight disagreements."""

        user_prompt = f"""USER QUESTION: {user_query}

RELEVANT DATA:
{context}

Answer based on this data. State consensus clearly. If analysts disagree, explain the split."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.5,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return message.content[0].text

    except Exception as e:
        return f"Error: {str(e)}"

# Sidebar
with st.sidebar:
    st.title("🥊 ChatMMA")
    st.markdown("---")

    # API Key input
    api_key = get_api_key()

    if not api_key:
        st.warning("⚠️ API Key Required")
        api_key = st.text_input(
            "Enter Claude API Key:",
            type="password",
            help="Get your key from console.anthropic.com"
        )
        if api_key:
            st.session_state.api_key = api_key.strip()
    else:
        st.success("✅ API Key Loaded")
        # Show first/last chars for debugging
        masked_key = f"{api_key[:10]}...{api_key[-10:]}" if len(api_key) > 20 else "***"
        st.caption(f"Key: {masked_key}")

        # Allow manual override
        override = st.checkbox("🔄 Override API Key", help="Use a different API key")
        if override:
            manual_key = st.text_input(
                "Enter new API Key:",
                type="password",
                help="This will override the stored key"
            )
            if manual_key:
                api_key = manual_key.strip()
                st.session_state.api_key = api_key
        else:
            st.session_state.api_key = api_key.strip()

    st.markdown("---")

    # Database stats and initialization
    if not os.path.exists("data/chatmma.db"):
        st.error("Database not found. Please run: `python scripts/init_database.py`")

        if st.button("🔧 Initialize Database Now", use_container_width=True):
            with st.spinner("Creating database..."):
                if init_database_if_needed():
                    st.success("✅ Database initialized successfully!")
                    st.rerun()
                else:
                    st.error("Failed to initialize database. Check the logs.")
    else:
        conn = get_database_connection()
        if conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM events')
            num_events = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM sources WHERE total_predictions > 0')
            num_analysts = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM predictions WHERE qa_status = "approved"')
            num_predictions = cursor.fetchone()[0]

            st.metric("Events", num_events)
            st.metric("Active Analysts", num_analysts)
            st.metric("Predictions", num_predictions)

            conn.close()

    st.markdown("---")
    st.markdown("### Navigation")
    page = st.radio("", ["💬 Chat", "📊 Analytics", "⚙️ Process Event"])

# Main content
if not st.session_state.api_key:
    st.title("🥊 Welcome to ChatMMA")
    st.markdown("""
    ## MMA Predictions Analysis

    ChatMMA synthesizes predictions from multiple expert analysts to give you:
    - **Consensus picks** weighted by analyst accuracy
    - **DFS insights** and betting advice
    - **Fighter analysis** and matchup breakdowns

    **👈 Enter your Claude API key in the sidebar to get started**

    Don't have an API key? Get one at [console.anthropic.com](https://console.anthropic.com)
    """)

elif page == "💬 Chat":
    st.title("💬 Chat with ChatMMA")

    # Chat interface
    st.markdown("Ask questions about fights, fighters, or predictions:")

    # Example queries
    with st.expander("💡 Example Questions"):
        st.markdown("""
        - "Who do analysts pick for the UFC 323 main event?"
        - "What are the best DFS picks for UFC 323?"
        - "Which analysts are most accurate?"
        - "Tell me about Petr Yan vs Merab Dvalishvili"
        - "Who's predicted to win by knockout?"
        """)

    # Chat input
    user_input = st.text_input("Your question:", key="chat_input")

    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.button("Ask", type="primary")
    with col2:
        clear = st.button("Clear History")

    if clear:
        st.session_state.chat_history = []
        st.rerun()

    if submit and user_input:
        with st.spinner("Thinking..."):
            response = chat_query(user_input, st.session_state.api_key)
            st.session_state.chat_history.append({
                "question": user_input,
                "answer": response,
                "time": datetime.now().strftime("%H:%M")
            })

    # Display chat history
    if st.session_state.chat_history:
        st.markdown("---")
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.container():
                st.markdown(f"**You ({chat['time']}):** {chat['question']}")
                st.markdown(f"**ChatMMA:** {chat['answer']}")
                st.markdown("---")

elif page == "📊 Analytics":
    st.title("📊 Analytics Dashboard")

    conn = get_database_connection()
    if not conn:
        st.stop()

    # Analyst Performance
    st.subheader("🎯 Analyst Performance")

    df_analysts = pd.read_sql_query('''
        SELECT
            analyst,
            type,
            accuracy_rate,
            total_predictions,
            correct_predictions
        FROM sources
        WHERE total_predictions > 0
        ORDER BY accuracy_rate DESC
    ''', conn)

    if not df_analysts.empty:
        # Format the dataframe
        df_analysts['Accuracy'] = df_analysts['accuracy_rate'].apply(lambda x: f"{x:.1f}%")
        df_analysts['Record'] = df_analysts.apply(
            lambda row: f"{row['correct_predictions']}/{row['total_predictions']}", axis=1
        )

        st.dataframe(
            df_analysts[['analyst', 'type', 'Accuracy', 'Record']].rename(columns={
                'analyst': 'Analyst',
                'type': 'Type'
            }),
            hide_index=True,
            use_container_width=True
        )

        # Bar chart
        import plotly.express as px
        fig = px.bar(
            df_analysts.head(10),
            x='analyst',
            y='accuracy_rate',
            color='type',
            title='Top 10 Analysts by Accuracy',
            labels={'analyst': 'Analyst', 'accuracy_rate': 'Accuracy %'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No analyst data yet. Process some events to see analytics.")

    st.markdown("---")

    # Recent Events
    st.subheader("📅 Recent Events")

    df_events = pd.read_sql_query('''
        SELECT
            name,
            date,
            location,
            fights_count,
            results_entered
        FROM events
        ORDER BY date DESC
        LIMIT 10
    ''', conn)

    if not df_events.empty:
        df_events['Results'] = df_events['results_entered'].apply(
            lambda x: "✅ Yes" if x else "❌ No"
        )
        st.dataframe(
            df_events[['name', 'date', 'location', 'fights_count', 'Results']].rename(columns={
                'name': 'Event',
                'date': 'Date',
                'location': 'Location',
                'fights_count': 'Fights'
            }),
            hide_index=True,
            use_container_width=True
        )

    conn.close()

elif page == "⚙️ Process Event":
    st.title("⚙️ Process Event")

    st.markdown("""
    Process a new UFC event to extract predictions and update the database.

    **Steps:**
    1. Select an event
    2. Click "Fetch Content" to download articles and transcripts
    3. Click "Extract Predictions" to use Claude API
    4. Click "Load to Database" to save predictions
    """)

    # Get available events
    import yaml
    try:
        with open('fights.yaml', 'r') as f:
            fights_data = yaml.safe_load(f)

        events = [event['name'] for event in fights_data['events']]

        selected_event = st.selectbox("Select Event:", events)

        # Quick load sample data button
        st.info("💡 **Quick Start:** Load sample UFC 323 data to test the app without fetching URLs")
        if st.button("⚡ Load Sample Data (UFC 323)", type="primary", use_container_width=True):
            with st.spinner("Loading sample predictions..."):
                try:
                    from load_to_db import load_predictions, update_analyst_stats
                    import glob

                    # Check if sample files exist
                    sample_files = glob.glob("data/extractions/UFC_323*.json")
                    if sample_files:
                        load_predictions("UFC 323")
                        update_analyst_stats()
                        st.success(f"✅ Loaded {len(sample_files)} sample predictions for UFC 323!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning("Sample data files not found in data/extractions/")
                except Exception as e:
                    st.error(f"Error loading sample data: {str(e)}")

        st.markdown("---")

        # Clear database button
        st.warning("⚠️ **Reset Data:** Clear all predictions to start fresh")
        if st.button("🗑️ Clear All Predictions", use_container_width=True):
            if st.session_state.get('confirm_clear', False):
                with st.spinner("Clearing predictions..."):
                    try:
                        conn = get_database_connection()
                        if conn:
                            cursor = conn.cursor()

                            # Delete all predictions
                            cursor.execute('DELETE FROM predictions')

                            # Reset analyst stats
                            cursor.execute('''
                                UPDATE sources
                                SET total_predictions = 0,
                                    correct_predictions = 0,
                                    accuracy_rate = 0.0
                            ''')

                            conn.commit()
                            conn.close()

                            st.success("✅ All predictions cleared!")
                            st.session_state.confirm_clear = False
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing data: {str(e)}")
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm deletion")
                st.rerun()

        st.markdown("---")
        st.markdown("### Manual Processing")
        st.caption("Use these steps to process new events:")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 Fetch Content"):
                with st.spinner("Fetching articles and transcripts..."):
                    # Import fetch functions
                    from fetch_articles import fetch_all_articles
                    from fetch_youtube import fetch_all_transcripts

                    articles_ok, articles_fail = fetch_all_articles(selected_event)
                    youtube_ok, youtube_fail = fetch_all_transcripts(selected_event)

                    st.success(f"✅ Fetched {articles_ok} articles, {youtube_ok} transcripts")
                    if articles_fail > 0 or youtube_fail > 0:
                        st.warning(f"⚠️ Failed: {articles_fail} articles, {youtube_fail} transcripts")

        with col2:
            if st.button("🤖 Extract Predictions"):
                with st.spinner("Extracting predictions with Claude..."):
                    from extract_picks import extract_all

                    try:
                        extract_all(selected_event)
                        st.success("✅ Predictions extracted!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        with col3:
            if st.button("💾 Load to Database"):
                with st.spinner("Loading to database..."):
                    from load_to_db import load_predictions, update_analyst_stats

                    try:
                        load_predictions(selected_event)
                        update_analyst_stats()
                        st.success("✅ Loaded to database!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.markdown("---")

        # Show recent extractions
        st.subheader("Recent Extractions")

        import glob
        extraction_files = glob.glob(f"data/extractions/*{selected_event.replace(' ', '_')}*.json")

        if extraction_files:
            st.success(f"Found {len(extraction_files)} extraction files for this event")

            for filepath in extraction_files[:3]:
                with st.expander(os.path.basename(filepath)):
                    import json
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    st.json(data)
        else:
            st.info("No extractions yet for this event")

    except Exception as e:
        st.error(f"Error loading events: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
ChatMMA MVP - Powered by Claude API | Built with Streamlit
</div>
""", unsafe_allow_html=True)
