import streamlit as st
from openai import OpenAI
import time
import json
import os
import tiktoken

# Set page config
st.set_page_config(
    page_title="AI Parameter Explorer",
    page_icon="🤖",
    layout="wide"
)

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

# Try to initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if api_key and st.session_state.client is None:
    try:
        st.session_state.client = OpenAI(api_key=api_key)
    except:
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

# Sidebar for API configuration
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Model selection
    model = st.selectbox(
        "Model",
        ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
        index=0
    )

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Input & Parameters")
    
    # Prompt input
    prompt = st.text_area(
        "Your Prompt",
        value="Write a short story about a robot learning to paint.",
        height=100,
        help="Enter the prompt you want to test with different parameters"
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
    
    # Max tokens
    max_tokens = st.slider(
        "Max Tokens",
        min_value=50,
        max_value=500,
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
    
    # Debug info - more detailed
    api_key_env = os.getenv('OPENAI_API_KEY')
    if api_key_env:
        st.success(f"🟢 API key found in environment (starts with: {api_key_env[:7]}...)")
        if st.session_state.client is None:
            st.error("🔴 But client failed to initialize!")
        else:
            st.success("🟢 OpenAI client ready")
    else:
        st.error("🔴 No OPENAI_API_KEY found in environment")
        st.info("Set with: `export OPENAI_API_KEY='your-key'` then restart Streamlit")
    
    # Display total cost
    if st.session_state.total_cost > 0:
        st.metric("💰 Total Session Cost", f"${st.session_state.total_cost:.4f}")
    
    # Generate button
    if st.button("🚀 Generate Response", type="primary", disabled=not st.session_state.client):
        if prompt.strip():
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
                    
                    # Calculate costs
                    input_tokens = count_tokens(prompt, model)
                    output_tokens = count_tokens(response_text, model)
                    cost = calculate_cost(input_tokens, output_tokens, model)
                    st.session_state.total_cost += cost
                    
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
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter a prompt")
    
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
                    st.write(f"📝 Tokens: {resp['input_tokens']} in → {resp['output_tokens']} out")
                
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
    st.subheader("🔁 Penalties")
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
    st.subheader("📝 What are Tokens?")
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
