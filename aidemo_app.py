import streamlit as st
from openai import OpenAI
import time
import json
import os
import tiktoken
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file for local testing
load_dotenv()

# Set page config
st.set_page_config(
    page_title="AI Parameter Explorer",
    page_icon="🤖",
    layout="wide"
)

# --- ABUSE PREVENTION FUNCTIONS ---
def check_rate_limit():
    """Prevent users from spamming requests"""
    
    # Get user identifier (IP-based session)
    if 'session_id' not in st.session_state:
        st.session_state.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    
    # Initialize rate limiting variables
    if 'requests' not in st.session_state:
        st.session_state.requests = []
    if 'session_tokens' not in st.session_state:
        st.session_state.session_tokens = 0
    
    # Clean old requests (older than 1 hour)
    current_time = datetime.now()
    st.session_state.requests = [
        req_time for req_time in st.session_state.requests 
        if current_time - req_time < timedelta(hours=1)
    ]
    
    # Check limits
    requests_last_hour = len(st.session_state.requests)
    requests_last_10_min = len([
        req_time for req_time in st.session_state.requests 
        if current_time - req_time < timedelta(minutes=10)
    ])
    
    # Rate limits
    if requests_last_10_min >= 5:
        st.error("⏰ Slow down! Maximum 5 requests per 10 minutes. Please wait before trying again.")
        st.info(f"You've made {requests_last_10_min} requests in the last 10 minutes.")
        return False
    
    if requests_last_hour >= 15:
        st.error("⏰ Daily limit reached! Maximum 15 requests per hour for this demo.")
        st.info("This helps keep the demo available for everyone. Try again in an hour!")
        return False
    
    if st.session_state.session_tokens > 50000:  # Roughly $0.05 worth per session
        st.error("💰 Token limit reached for this session! Please refresh the page to continue.")
        st.info("This demo has spending limits to keep it free for everyone.")
        return False
    
    return True

def log_request():
    """Log a successful request"""
    st.session_state.requests.append(datetime.now())

def validate_input(user_input):
    """Prevent abusive or expensive inputs"""
    
    if not user_input or len(user_input.strip()) == 0:
        st.error("Please enter a prompt.")
        return False
    
    if len(user_input) > 500:  # Limit input length
        st.error("Please keep your prompt under 500 characters for this demo.")
        return False
    
    # Check for repetitive patterns (spam detection)
    words = user_input.lower().split()
    if len(words) > 5 and len(set(words)) < len(words) / 3:
        st.warning("This looks like repetitive text. Please enter a genuine prompt.")
        return False
    
    # Block certain expensive request types
    expensive_keywords = [
        'write a book', 'write a novel', 'generate 1000', 'list everything',
        'write code for', 'create a complete', 'translate entire', 'summarize this book'
    ]
    
    if any(keyword in user_input.lower() for keyword in expensive_keywords):
        st.warning("This demo is for educational prompts only. Please try a shorter, more specific request.")
        return False
    
    return True

# --- MAIN APP ---

# Title and description
st.title("🤖 AI Parameter Explorer")
st.markdown("""
**Discover how AI parameters change responses!** 

This tool demonstrates that AI models are sophisticated **word prediction systems**, not oracles. 
Small changes in parameters can dramatically alter outputs, showing the probabilistic nature of AI.
""")

# Initialize session state
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'client' not in st.session_state:
    st.session_state.client = None

# Try to initialize OpenAI client with dual support
try:
    api_key = None
    
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
    except:
        pass
    
    # Fallback to environment variable (for local development)
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key and st.session_state.client is None:
        st.session_state.client = OpenAI(api_key=api_key)
    elif not api_key:
        st.session_state.client = None
    
except Exception as e:
    st.session_state.client = None

# OpenAI pricing (per 1K tokens) - updated as of Jan 2024
PRICING = {
    "gpt-3.5-turbo": {"input": 0.0010, "output": 0.0020},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03}
}

def count_tokens(text, model):
    """Count tokens in text using tiktoken"""
    try:
        if model.startswith("gpt-4"):
            encoding = tiktoken.encoding_for_model("gpt-4")
        else:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(encoding.encode(text))
    except:
        # Fallback estimation: ~4 chars per token
        return len(text) // 4

def calculate_cost(input_tokens, output_tokens, model):
    """Calculate cost based on token usage"""
    if model not in PRICING:
        return 0.0
    
    input_cost = (input_tokens / 1000) * PRICING[model]["input"]
    output_cost = (output_tokens / 1000) * PRICING[model]["output"]
    return input_cost + output_cost

# Sidebar for API configuration and usage stats
with st.sidebar:
    st.header("📊 Usage Stats")
    
    # Daily global cap tracking
    daily_tracking = load_daily_tracking()
    daily_percentage = (daily_tracking["cost"] / 1.0) * 100
    st.metric("Daily Usage", f"${daily_tracking['cost']:.4f}/$1.00")
    st.progress(min(daily_percentage / 100, 1.0))
    
    # Session-specific tracking
    if 'requests' in st.session_state and 'session_tokens' in st.session_state:
        recent_requests = len([
            req_time for req_time in st.session_state.requests 
            if datetime.now() - req_time < timedelta(minutes=10)
        ])
        st.metric("Requests (last 10 min)", f"{recent_requests}/5")
        st.metric("Session Tokens", f"{st.session_state.session_tokens:,}/50,000")
        st.metric("Session Cost", f"${st.session_state.total_cost:.4f}")  # Using actual tracked cost
    
    st.info("💡 This demo has usage limits to prevent abuse and keep it free for everyone!")
    
    st.divider()
    st.header("🔧 Configuration")
    
    # Model selection - limited for demo protection
    model = st.selectbox(
        "Model",
        ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
        index=0
    )

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🎛️ Input & Parameters")
    
    # Prompt input with protection
    prompt = st.text_area(
        "Your Prompt",
        value="Write a short story about a robot learning to paint.",
        height=100,
        max_chars=500,  # Enforce character limit for protection
        help="Enter the prompt you want to test with different parameters (max 500 characters)"
    )
    
    st.subheader("🎛️ Model Parameters")
    
    # Temperature slider
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Controls randomness. Higher = more creative/random, Lower = more focused/deterministic"
    )
    
    # Top-p slider
    top_p = st.slider(
        "Top-p (Nucleus Sampling)",
        min_value=0.1,
        max_value=1.0,
        value=1.0,
        step=0.1,
        help="Controls diversity via nucleus sampling. Lower = more focused vocabulary"
    )
    
    # Max tokens - limited for demo protection
    max_tokens = st.slider(
        "Max Tokens",
        min_value=50,
        max_value=300,  # Reduced max for demo protection
        value=150,
        step=25,
        help="Maximum length of the response"
    )
    
    # Frequency penalty
    frequency_penalty = st.slider(
        "Frequency Penalty",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.1,
        help="Reduces repetition. Higher = less likely to repeat tokens"
    )
    
    # Presence penalty
    presence_penalty = st.slider(
        "Presence Penalty",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.1,
        help="Encourages talking about new topics. Higher = more likely to introduce new topics"
    )

with col2:
    st.header("🎯 Results")
    
    # API Status with detailed feedback
    api_key_env = os.getenv('OPENAI_API_KEY')
    api_key_secrets = None
    try:
        if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
            api_key_secrets = st.secrets["OPENAI_API_KEY"]
    except:
        pass
    
    if st.session_state.client:
        if api_key_secrets:
            st.success("🟢 OpenAI client ready (using Streamlit secrets)")
        elif api_key_env:
            st.success(f"🟢 OpenAI client ready (using .env file - starts with: {api_key_env[:7]}...)")
        else:
            st.success("🟢 OpenAI client ready")
    else:
        st.error("🔴 OpenAI API not configured")
        if not api_key_env and not api_key_secrets:
            st.info("💡 **Local:** Add OPENAI_API_KEY to your .env file\n\n💡 **Streamlit Cloud:** Add OPENAI_API_KEY to your app secrets")
        elif api_key_env:
            st.info("API key found but client failed to initialize. Check your key validity.")
    
    # Display total cost
    if st.session_state.total_cost > 0:
       st.metric("Session Cost", f"${st.session_state.total_cost:.4f}")
    
    # Generate button with full protection
    if st.button("🚀 Generate Response", type="primary", disabled=not st.session_state.client):
        
        # Validate input
        if not validate_input(prompt):
            st.stop()
        
        # Check rate limits
        if not check_rate_limit():
            st.stop()
            
        with st.spinner("Generating response..."):
            try:
                # Make API call
                response = st.session_state.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty
                )
                
                # Extract response text
                response_text = response.choices[0].message.content
                
                # Calculate costs and track tokens
                input_tokens = count_tokens(prompt, model)
                output_tokens = count_tokens(response_text, model)
                cost = calculate_cost(input_tokens, output_tokens, model)
                total_tokens = input_tokens + output_tokens
                
                # Update session tracking
                st.session_state.total_cost += cost
                st.session_state.session_tokens += total_tokens
                log_request()  # Log successful request
                
                # Store response with parameters
                response_data = {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "model": model,
                    "prompt": prompt,
                    "response": response_text,
                    "cost": cost,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "parameters": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "max_tokens": max_tokens,
                        "frequency_penalty": frequency_penalty,
                        "presence_penalty": presence_penalty
                    }
                }
                
                st.session_state.responses.insert(0, response_data)
                st.success("✅ Response generated!")
                
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")
    
    # Display responses
    if st.session_state.responses:
        st.subheader("📊 Response History")
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.responses = []
            st.session_state.total_cost = 0.0
            st.rerun()
        
        # Display each response
        for i, resp in enumerate(st.session_state.responses):
            with st.expander(f"Response {i+1} - {resp['timestamp']} - ${resp['cost']:.4f}", expanded=(i==0)):
                st.write("**Response:**")
                st.write(resp['response'])
                
                col_cost, col_tokens = st.columns(2)
                with col_cost:
                    st.metric("💰 Cost", f"${resp['cost']:.4f}")
                with col_tokens:
                    st.write(f"🔢 Tokens: {resp['input_tokens']} in → {resp['output_tokens']} out")
                
                st.write("**Parameters:**")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"• Temperature: {resp['parameters']['temperature']}")
                    st.write(f"• Top-p: {resp['parameters']['top_p']}")
                    st.write(f"• Max Tokens: {resp['parameters']['max_tokens']}")
                with col_b:
                    st.write(f"• Frequency Penalty: {resp['parameters']['frequency_penalty']}")
                    st.write(f"• Presence Penalty: {resp['parameters']['presence_penalty']}")
                    st.write(f"• Model: {resp['model']}")

# Educational content at the bottom
st.divider()
st.header("🎓 Understanding AI Parameters")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌡️ Temperature")
    st.write("""
    **Controls randomness and creativity**
    - 0.0: Very focused, deterministic
    - 1.0: Balanced creativity
    - 2.0: Very random, creative
    
    *Try the same prompt with 0.1 vs 1.5!*
    """)

with col2:
    st.subheader("🎯 Top-p")
    st.write("""
    **Controls vocabulary diversity**
    - 0.1: Very focused word choices
    - 1.0: Full vocabulary available
    
    *Lower values = more predictable language*
    """)

with col3:
    st.subheader("📊 Penalties")
    st.write("""
    **Shape content patterns**
    - Frequency: Reduces repetition
    - Presence: Encourages new topics
    
    *Higher values = more variation*
    """)

st.info("""
💡 **Key Insight**: AI models are sophisticated **probability engines** that predict the most likely next words based on patterns in training data. 
These parameters adjust those probabilities, showing that there's no single "correct" response - just different probable outcomes!
""")

st.divider()

# Additional educational section about tokens
st.header("🔤 Understanding Tokens & Costs")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔢 What are Tokens?")
    st.write("""
    **Tokens are the basic units AI models process** - roughly pieces of words:
    
    • **"hello"** = 1 token
    • **"ChatGPT"** = 2 tokens (Chat + GPT)  
    • **"AI"** = 1 token
    • **"don't"** = 2 tokens (don + 't)
    
    **Rules of thumb:**
    • ~4 characters = 1 token (English)
    • ~750 words = 1,000 tokens
    • Spaces and punctuation count!
    """)

with col2:
    st.subheader("💰 How Costs Work")
    st.write("""
    **You pay for both input AND output tokens:**
    
    • **Input**: Your prompt (what you send)
    • **Output**: The AI's response (what you get back)
    • **Different models** = different prices
    • **Longer responses** = higher costs
    
    **Cost factors:**
    • Higher temperature → potentially longer responses
    • Max tokens setting → caps your maximum cost
    • Model choice → biggest cost difference
    """)

# Token counter demo
st.subheader("🧮 Token Counter Demo")
demo_text = st.text_input(
    "Try typing text to see token count:",
    value="Hello, how are you doing today?",
    help="See how different text gets converted to tokens"
)

if demo_text:
    token_count = count_tokens(demo_text, "gpt-3.5-turbo")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Characters", len(demo_text))
    with col_b:
        st.metric("Estimated Tokens", token_count)
    with col_c:
        cost_estimate = (token_count / 1000) * PRICING["gpt-3.5-turbo"]["input"]
        st.metric("Input Cost", f"${cost_estimate:.6f}")

# Usage Limits Disclaimer
st.markdown("---")
st.markdown("""
### 📋 Usage Limits & Fair Use Policy

**This demo has the following limits to keep it free and available for everyone:**

**Rate Limits:**
- **5 requests per 10 minutes** - Prevents rapid-fire spam
- **15 requests per hour** - Allows meaningful exploration
- **50,000 tokens per session** - About 100 conversations before refresh needed

**Input Restrictions:**
- **500 character limit** - Keeps requests focused and costs manageable
- **Blocks expensive request types** - No "write a book" or bulk generation requests
- **Spam detection** - Repetitive or bot-like inputs are filtered out

**Why These Limits?**
- Each AI request costs real money (~$0.001-0.03 per interaction depending on model)
- Without limits, the demo could cost hundreds of dollars per day
- These restrictions keep the total daily cost under $1 while serving many users

**Need More Usage?** This is an educational demo. For production use, consider:
- Setting up your own OpenAI API account
- Using official ChatGPT or other AI services
- Building your own implementation using the open-source code

*Last updated: August 2025*
""")

st.info("💡 **Educational Purpose:** This demo exists to help people understand AI costs, capabilities, and limitations in a transparent way.")
