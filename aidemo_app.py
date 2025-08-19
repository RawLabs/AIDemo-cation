import streamlit as st
import time
import hashlib
from datetime import datetime, timedelta

# --- RATE LIMITING ---
def check_rate_limit():
    """Prevent users from spamming requests"""
    
    # Get user identifier (IP-based session)
    if 'session_id' not in st.session_state:
        # Create a session identifier
        st.session_state.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    
    # Initialize rate limiting variables
    if 'requests' not in st.session_state:
        st.session_state.requests = []
    if 'total_tokens' not in st.session_state:
        st.session_state.total_tokens = 0
    
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
    
    if st.session_state.total_tokens > 50000:  # Roughly $0.05 worth per session
        st.error("💰 Token limit reached for this session! Please refresh the page to continue.")
        st.info("This demo has spending limits to keep it free for everyone.")
        return False
    
    return True

def log_request():
    """Log a successful request"""
    st.session_state.requests.append(datetime.now())

# --- INPUT VALIDATION ---
def validate_input(user_input):
    """Prevent abusive or expensive inputs"""
    
    if not user_input or len(user_input.strip()) == 0:
        st.error("Please enter a question or prompt.")
        return False
    
    if len(user_input) > 500:  # Limit input length
        st.error("Please keep your input under 500 characters for this demo.")
        return False
    
    # Check for repetitive patterns (spam detection)
    if len(set(user_input.lower().split())) < len(user_input.split()) / 3:
        st.warning("This looks like repetitive text. Please enter a genuine question.")
        return False
    
    # Block certain expensive request types
    expensive_keywords = [
        'write a book', 'write a novel', 'generate 1000', 'list everything',
        'write code for', 'create a complete', 'translate entire', 'summarize this book'
    ]
    
    if any(keyword in user_input.lower() for keyword in expensive_keywords):
        st.warning("This demo is for quick questions only. Please try a shorter, more specific request.")
        return False
    
    return True

# --- COST TRACKING ---
def estimate_cost(prompt, response=""):
    """Estimate and track API costs"""
    
    # Rough token estimation (1 token ≈ 4 characters for English)
    prompt_tokens = len(prompt) // 4
    response_tokens = len(response) // 4
    total_tokens = prompt_tokens + response_tokens
    
    # Update session totals
    st.session_state.total_tokens += total_tokens
    
    # Cost estimation (GPT-3.5-turbo pricing: ~$0.001/1k tokens average)
    estimated_cost = (total_tokens / 1000) * 0.001
    
    return total_tokens, estimated_cost

# --- MAIN DEMO FUNCTION ---
def safe_ai_demo():
    """AI demo with built-in abuse prevention"""
    
    st.title("🤖 AI Demo - How It Works & Costs")
    
    # Show current usage stats
    with st.sidebar:
        st.header("📊 Usage Stats")
        if 'requests' in st.session_state:
            recent_requests = len([
                req_time for req_time in st.session_state.requests 
                if datetime.now() - req_time < timedelta(minutes=10)
            ])
            st.metric("Requests (last 10 min)", f"{recent_requests}/5")
            st.metric("Total Tokens Used", st.session_state.total_tokens)
            st.metric("Estimated Cost", f"${(st.session_state.total_tokens / 1000) * 0.001:.4f}")
        
        st.info("💡 This demo has usage limits to prevent abuse and keep it free for everyone!")
    
    # Main interface
    st.write("Ask the AI a question and see how it processes your request, including real costs!")
    
    user_input = st.text_area(
        "Your question:", 
        placeholder="e.g., 'Explain quantum computing in simple terms'",
        max_chars=500
    )
    
    if st.button("Ask AI", type="primary"):
        
        # Validate input
        if not validate_input(user_input):
            return
        
        # Check rate limits
        if not check_rate_limit():
            return
        
        # Log the request
        log_request()
        
        with st.spinner("🤔 AI is thinking..."):
            try:
                # Your OpenAI API call here
                # client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                # response = client.chat.completions.create(...)
                
                # For demo purposes:
                response_text = f"This is a demo response to: '{user_input}'"
                
                # Track costs
                total_tokens, estimated_cost = estimate_cost(user_input, response_text)
                
                # Display results
                st.success("✅ Response received!")
                st.write("**AI Response:**")
                st.write(response_text)
                
                # Show transparency info
                with st.expander("📊 Behind the Scenes"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tokens Used", total_tokens)
                        st.metric("Estimated Cost", f"${estimated_cost:.4f}")
                    with col2:
                        st.write("**What just happened:**")
                        st.write("1. Your text was tokenized")
                        st.write("2. Sent to OpenAI's servers")
                        st.write("3. Processed by AI model")
                        st.write("4. Response generated & returned")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return
    
    # Educational content
    st.markdown("---")
    st.header("🎓 What You're Learning")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Real Costs")
        st.write("Every AI request costs money:")
        st.write("- Input processing: ~$0.0015/1K tokens")
        st.write("- Output generation: ~$0.002/1K tokens") 
        st.write("- A conversation can cost $0.01-0.10+")
    
    with col2:
        st.subheader("⚡ Why Limits Matter")
        st.write("Without protection:")
        st.write("- Bots could spam expensive requests")
        st.write("- Costs could spiral out of control") 
        st.write("- Demo would shut down quickly")
    
    # Rate Limits Disclaimer
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
    - Each AI request costs real money (~$0.0005-0.002 per interaction)
    - Without limits, the demo could cost hundreds of dollars per day
    - These restrictions keep the total daily cost under $1 while serving many users
    
    **Need More Usage?** This is an educational demo. For production use, consider:
    - Setting up your own OpenAI API account
    - Using official ChatGPT or other AI services
    - Building your own implementation using the open-source code
    
    *Last updated: August 2025*
    """)
    
    st.info("💡 **Educational Purpose:** This demo exists to help people understand AI costs, capabilities, and limitations in a transparent way.")

# Run the protected demo
if __name__ == "__main__":
    safe_ai_demo()
