import base64
import threading

import ollama
import streamlit as st

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI2 Chatbot", page_icon="🤖", layout="centered")

DEFAULT_MODEL = "llama3.2"
MAX_HISTORY = 8  # how many recent messages the AI reads (less to read = faster)

# One neutral instruction: answer the LATEST message using the conversation so far.
SYSTEM_PROMPT = (
    "You are a helpful AI assistant in an ongoing conversation. "
    "Always answer the user's latest message directly. "
    "Use the earlier messages as context, so follow-up questions like 'why?' or "
    "'give an example' refer to what was just discussed. "
    "Do not repeat earlier answers, do not add unrelated information, "
    "and keep replies clear and to the point."
)

# Shorter answers = much faster replies. (instruction, max tokens)
LENGTHS = {
    "Short": ("Reply in 2 to 4 sentences.", 200),
    "Medium": ("Reply in one short paragraph or a few bullet points.", 400),
    "Detailed": ("Give a thorough, well-organized answer.", 900),
}

# ---------------------------------------------------------------------------
# Illustration (drawn in code, no external images needed)
# ---------------------------------------------------------------------------
ROBOT_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 170">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7C5CFF"/><stop offset="1" stop-color="#22C7A9"/>
    </linearGradient>
    <linearGradient id="h" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E6E1FF"/>
    </linearGradient>
  </defs>
  <g stroke="#B9AEFF" stroke-width="1.6" opacity="0.8">
    <line x1="18" y1="34" x2="52" y2="78"/><line x1="52" y1="78" x2="24" y2="128"/>
    <line x1="52" y1="78" x2="70" y2="140"/><line x1="18" y1="34" x2="60" y2="22"/>
    <line x1="222" y1="40" x2="190" y2="84"/><line x1="190" y1="84" x2="218" y2="132"/>
    <line x1="190" y1="84" x2="172" y2="146"/><line x1="222" y1="40" x2="180" y2="20"/>
  </g>
  <g fill="#7C5CFF" opacity="0.85">
    <circle cx="18" cy="34" r="5"/><circle cx="52" cy="78" r="6"/><circle cx="24" cy="128" r="5"/>
    <circle cx="70" cy="140" r="4"/><circle cx="60" cy="22" r="4"/>
    <circle cx="222" cy="40" r="5"/><circle cx="190" cy="84" r="6"/><circle cx="218" cy="132" r="5"/>
    <circle cx="172" cy="146" r="4"/><circle cx="180" cy="20" r="4"/>
  </g>
  <line x1="120" y1="20" x2="120" y2="40" stroke="#5B3FE0" stroke-width="4" stroke-linecap="round"/>
  <circle cx="120" cy="15" r="8" fill="#FF6FA5"/>
  <rect x="72" y="40" width="96" height="78" rx="24" fill="url(#h)" stroke="#5B3FE0" stroke-width="4"/>
  <rect x="59" y="68" width="13" height="26" rx="6" fill="#5B3FE0"/>
  <rect x="168" y="68" width="13" height="26" rx="6" fill="#5B3FE0"/>
  <rect x="84" y="56" width="72" height="44" rx="16" fill="#2A2470"/>
  <circle cx="104" cy="76" r="8" fill="#5EEAD4"/><circle cx="136" cy="76" r="8" fill="#5EEAD4"/>
  <circle cx="107" cy="73" r="2.6" fill="#FFFFFF"/><circle cx="139" cy="73" r="2.6" fill="#FFFFFF"/>
  <path d="M108 91 Q120 100 132 91" stroke="#5EEAD4" stroke-width="3.4" fill="none" stroke-linecap="round"/>
  <rect x="92" y="124" width="56" height="34" rx="13" fill="url(#g)"/>
  <circle cx="120" cy="141" r="5.5" fill="#FFFFFF"/>
  <path d="M204 66 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" fill="#FFC857"/>
  <path d="M36 96 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2z" fill="#FF6FA5"/>
</svg>
"""
ROBOT_URI = "data:image/svg+xml;base64," + base64.b64encode(ROBOT_SVG.encode()).decode()

# ---------------------------------------------------------------------------
# CSS  (dark text on light colours, so words are always visible)
# ---------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #1E1B4B;
    --muted: #6B6899;
    --surface: #FFFFFF;
    --accent: #6C4CF1;
    --accent2: #22C7A9;
    --pink: #FF6FA5;
    --accent-soft: #EFEBFF;
    --line: #DCD3FF;
}

html, body, .stApp {
    font-family: 'Poppins', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at 12% 8%, #E4DCFF 0, transparent 38%),
        radial-gradient(circle at 92% 18%, #FFE0EE 0, transparent 34%),
        radial-gradient(circle at 85% 92%, #D5F7EE 0, transparent 38%),
        #F8F7FF;
    background-attachment: fixed;
}

.stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp div,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stSidebar"], [data-testid="stSidebar"] * {
    color: var(--ink) !important;
}
p, li { font-size: 1.02rem; }

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 800px; padding-top: 1.5rem; padding-bottom: 7rem; }

/* Hero banner */
.hero {
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    background: linear-gradient(135deg, #FFFFFF 0%, #F1ECFF 100%);
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 30px rgba(108, 76, 241, 0.12);
}
.hero-title {
    font-size: 2.3rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1;
    background: linear-gradient(90deg, #6C4CF1, #FF6FA5);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent !important;
}
.hero-sub { margin: 0.4rem 0 0.7rem 0; color: var(--muted) !important; font-size: 1rem; }
.hero-chip {
    display: inline-block; padding: 0.25rem 0.8rem; border-radius: 999px;
    background: var(--accent-soft); border: 1px solid var(--line);
    font-size: 0.82rem; font-weight: 600;
}
.hero img { width: 210px; max-width: 38vw; flex-shrink: 0; }

/* Chat bubbles */
[data-testid="stChatMessage"] {
    background: var(--surface) !important;
    border: 1px solid var(--line);
    border-left: 5px solid var(--accent2);
    border-radius: 18px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 4px 14px rgba(30, 27, 75, 0.06);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, #EFEBFF, #FFEAF3) !important;
    border-left: 5px solid var(--pink);
}
[data-testid="stChatMessage"] p { line-height: 1.65; }

/* Typing animation */
.typing span {
    display: inline-block; width: 9px; height: 9px; margin: 6px 4px 2px 0;
    border-radius: 50%; background: var(--accent);
    animation: bounce 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: 0.15s; background: var(--pink); }
.typing span:nth-child(3) { animation-delay: 0.3s; background: var(--accent2); }
@keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
    40% { transform: translateY(-7px); opacity: 1; }
}

/* Bottom bar and typing box */
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent !important; }
[data-testid="stChatInput"] {
    border: 2px solid var(--line); border-radius: 18px; background: var(--surface) !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent); box-shadow: 0 0 0 4px rgba(108, 76, 241, 0.15);
}
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] div {
    background: var(--surface) !important; color: var(--ink) !important; caret-color: var(--accent);
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; opacity: 1; }

/* Sidebar */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #F7F5FF !important; color: var(--ink) !important; border-radius: 12px;
}
.status-ok, .status-bad {
    display: inline-block; padding: 0.2rem 0.75rem; border-radius: 999px;
    font-size: 0.82rem; font-weight: 600; margin-bottom: 0.6rem;
}
.status-ok  { background: #D5F7EE; }
.status-bad { background: #FFE0E6; }

/* Dropdown list */
[data-baseweb="popover"], [data-baseweb="popover"] *,
[data-baseweb="menu"], [data-baseweb="menu"] * {
    background: #FFFFFF !important; color: var(--ink) !important;
}
[data-baseweb="menu"] li:hover, [data-baseweb="menu"] [aria-selected="true"] {
    background: var(--accent-soft) !important;
}

/* Slider */
[data-testid="stSlider"] [role="slider"] { background: var(--accent) !important; }
[data-testid="stSlider"] [data-baseweb="slider"] div[style*="linear-gradient"] {
    background: linear-gradient(to right, var(--accent) 0%, var(--accent) 100%) !important;
}
[data-testid="stSliderThumbValue"], [data-testid="stSliderThumbValue"] * { color: var(--accent) !important; }

/* Toolbar */
[data-testid="stToolbar"] *, [data-testid="stStatusWidget"] * { color: var(--ink) !important; }

/* Buttons */
.stButton > button {
    background: var(--surface) !important; color: var(--ink) !important;
    border: 1.5px solid var(--line); border-radius: 14px;
    font-weight: 600; width: 100%; padding: 0.6rem 0.9rem;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: var(--accent); background: var(--accent-soft) !important;
    box-shadow: 0 6px 16px rgba(108, 76, 241, 0.16);
}

/* Code blocks and alerts */
code, pre, [data-testid="stCode"] { background: #F1EEFF !important; color: var(--ink) !important; border-radius: 10px; }
[data-testid="stAlert"] { background: var(--accent-soft) !important; border: 1px solid var(--line); }
[data-testid="stAlert"] * { color: var(--ink) !important; }

@media (max-width: 640px) {
    .hero { flex-direction: column-reverse; text-align: center; }
    .hero-title { font-size: 1.8rem; }
    .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

TYPING_HTML = '<div class="typing"><span></span><span></span><span></span></div>'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ollama_is_running() -> bool:
    try:
        ollama.list()
        return True
    except Exception:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def get_installed_models() -> list:
    """Models installed in Ollama (works with old and new ollama versions)."""
    try:
        data = ollama.list()
        models = data["models"] if isinstance(data, dict) else data.models
        names = []
        for m in models:
            if isinstance(m, dict):
                name = m.get("model") or m.get("name")
            else:
                name = getattr(m, "model", None) or getattr(m, "name", None)
            if name:
                names.append(name)
        return names or [DEFAULT_MODEL]
    except Exception:
        return [DEFAULT_MODEL]


@st.cache_resource(show_spinner=False)
def warm_up(model: str) -> bool:
    """Load the model into memory in the background, so the first answer is not slow."""
    def _load():
        try:
            ollama.chat(model=model, messages=[], keep_alive="30m")
        except Exception:
            pass
    threading.Thread(target=_load, daemon=True).start()
    return True


def generate_reply(model, context, temperature, max_tokens, placeholder):
    """Stream the answer into `placeholder`; typing animation shows until text arrives."""
    placeholder.markdown(TYPING_HTML, unsafe_allow_html=True)
    full = ""
    stream = ollama.chat(
        model=model,
        messages=context,
        stream=True,
        options={"temperature": temperature, "num_ctx": 2048, "num_predict": max_tokens},
        keep_alive="30m",  # keep the model in memory between questions
    )
    for chunk in stream:
        piece = chunk["message"]["content"]
        if piece:
            full += piece
            placeholder.markdown(full + " ▌")
    placeholder.markdown(full)
    return full


# ---------------------------------------------------------------------------
# Session state: the live conversation (only exists while this page is open)
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("✨ Settings")

    if ollama_is_running():
        st.markdown('<span class="status-ok">● Ollama is running</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-bad">● Ollama is not running</span>', unsafe_allow_html=True)
        st.caption("Open the Ollama app, or run `ollama serve` in a terminal.")

    models = get_installed_models()
    model = st.selectbox(
        "Model",
        models,
        index=models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0,
    )
    length = st.selectbox(
        "Answer length", list(LENGTHS.keys()),
        help="Short answers arrive much faster.",
    )
    temperature = st.slider(
        "Creativity", 0.0, 1.2, 0.6, 0.1,
        help="Lower = focused and accurate. Higher = more imaginative.",
    )
    warm_up(model)

    st.divider()
    if st.button("🗑️ New chat"):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# New question
# ---------------------------------------------------------------------------
prompt = st.chat_input("Ask me anything...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f'<div class="hero"><div>'
    f'<div class="hero-title">AI2 Chatbot</div>'
    f'<p class="hero-sub">Ask me anything. I answer based on our conversation.</p>'
    f'<span class="hero-chip">{model}</span>'
    f'</div><img src="{ROBOT_URI}" alt="AI robot"/></div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Show conversation
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    avatar = "🧑‍🎓" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Answer the new question using the conversation so far
# ---------------------------------------------------------------------------
if prompt:
    length_note, max_tokens = LENGTHS[length]
    context = [{"role": "system", "content": SYSTEM_PROMPT + " " + length_note}]
    context += st.session_state.messages[-MAX_HISTORY:]

    with st.chat_message("assistant", avatar="🤖"):
        box = st.empty()
        try:
            reply = generate_reply(model, context, temperature, max_tokens, box)
            if not reply.strip():
                box.warning("The model returned an empty answer. Try asking again.")
            else:
                st.session_state.messages.append({"role": "assistant", "content": reply})
        except ollama.ResponseError as e:
            box.error(f"Ollama error: {e.error}\n\nIf the model is missing, run:  ollama pull {model}")
        except Exception as e:
            box.error(
                "Could not get an answer from Ollama. Make sure the Ollama app is running.\n\n"
                f"Details: {e}"
            )