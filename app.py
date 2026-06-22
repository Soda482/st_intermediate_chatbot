import streamlit as st
import os
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import httpx

# 加载环境变量
load_dotenv()

# 聊天风格定义
STYLES = {
    "标准正式": {
        "description": "语气严谨、逻辑清晰、用词规范",
        "prompt": "请以标准正式的语气回答，保持中立客观，逻辑清晰，用词规范。"
    },
    "简约干练": {
        "description": "短句为主、直击重点、少废话",
        "prompt": "请用最简洁的语言直接回答问题，直击要点，不添加多余内容。"
    },
    "温和亲切": {
        "description": "语气柔软、有耐心，像朋友/助教",
        "prompt": "请用温和亲切的语气回答，像朋友聊天一样，带点语气词，让用户感到温暖。"
    },
    "中二/次元": {
        "description": "动漫、网文语感，台词感强",
        "prompt": "请用二次元/动漫风格回答，使用动漫台词风格，充满中二气息。"
    },
    "高冷寡言": {
        "description": "话少、语气冷淡、简洁",
        "prompt": "请用高冷寡言的风格回答，话少且简洁，语气冷淡，不主动搭话。"
    },
    "毒舌吐槽": {
        "description": "言语犀利、爱吐槽，语气带调侃",
        "prompt": "请用毒舌吐槽的风格回答，言语犀利，带有调侃和幽默。"
    },
    "职场干练": {
        "description": "商务口吻、专业得体",
        "prompt": "请用职场商务风格回答，专业得体，适合办公沟通。"
    },
    "文艺诗意": {
        "description": "用词优美、有画面感",
        "prompt": "请用文艺诗意的风格回答，用词优美，富有画面感和抒情性。"
    },
    "古风文言": {
        "description": "古风措辞、半文言/纯文言",
        "prompt": "请用古风文言风格回答，使用半文言或纯文言，符合古风语境。"
    },
    "辩论/思辨": {
        "description": "逻辑严谨、多角度分析",
        "prompt": "请用辩论思辨风格回答，逻辑严谨，从多个角度分析问题，有理有据。"
    }
}

def init_session_state():
    """初始化会话状态"""
    if "conversations" not in st.session_state:
        st.session_state.conversations = []
        load_conversations()
    
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("API_KEY", "")
    
    if "base_url" not in st.session_state:
        st.session_state.base_url = os.getenv("BASE_URL", "https://api.deepseek.com/v1")
    
    if "model" not in st.session_state:
        st.session_state.model = os.getenv("MODEL", "deepseek-v4-pro")
    
    if "temperature" not in st.session_state:
        st.session_state.temperature = float(os.getenv("TEMPERATURE", "0.7"))
    
    if "selected_style" not in st.session_state:
        st.session_state.selected_style = "标准正式"
    
    if "custom_prompt" not in st.session_state:
        st.session_state.custom_prompt = ""
    
    if "show_avatar" not in st.session_state:
        st.session_state.show_avatar = True

def generate_title(messages, max_len=30):
    """根据对话内容生成标题"""
    if not messages:
        return "新对话"
    first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
    title = first_user_msg[:max_len]
    if len(first_user_msg) > max_len:
        title += "..."
    return title if title else "新对话"

def generate_conversation_id():
    """生成唯一对话ID"""
    return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()

def save_conversations():
    """保存对话到本地文件"""
    try:
        with open("conversations.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.conversations, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存对话失败: {str(e)}")

def load_conversations():
    """从本地文件加载对话"""
    try:
        if os.path.exists("conversations.json"):
            with open("conversations.json", "r", encoding="utf-8") as f:
                st.session_state.conversations = json.load(f)
    except Exception as e:
        st.warning(f"加载对话失败: {str(e)}")

def start_new_conversation():
    """开始新对话"""
    st.session_state.current_conversation = generate_conversation_id()
    st.session_state.messages = []

def select_conversation(conversation):
    """选择对话"""
    st.session_state.current_conversation = conversation["id"]
    st.session_state.messages = conversation["messages"].copy()

def delete_conversation(conversation_id):
    """删除对话"""
    st.session_state.conversations = [c for c in st.session_state.conversations if c["id"] != conversation_id]
    if st.session_state.current_conversation == conversation_id:
        st.session_state.current_conversation = None
        st.session_state.messages = []
    save_conversations()

def get_style_prompt():
    """获取风格提示词"""
    style = st.session_state.selected_style
    base_prompt = STYLES.get(style, STYLES["标准正式"])["prompt"]
    if st.session_state.custom_prompt:
        base_prompt += f"\n\n额外要求：{st.session_state.custom_prompt}"
    return base_prompt

def call_llm_api(messages):
    """调用LLM API"""
    api_key = st.session_state.api_key
    base_url = st.session_state.base_url
    model = st.session_state.model
    temperature = st.session_state.temperature
    
    if not api_key:
        raise ValueError("请先配置API Key")
    
    # 构建完整消息
    style_prompt = get_style_prompt()
    system_msg = {"role": "system", "content": style_prompt}
    full_messages = [system_msg] + messages
    
    try:
        client = httpx.Client(timeout=60)
        response = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": full_messages,
                "temperature": temperature,
                "stream": True
            }
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        json_data = json.loads(data)
                        content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except httpx.HTTPError as e:
        raise Exception(f"网络请求失败: {str(e)}")
    except ValueError as e:
        raise ValueError(f"API配置错误: {str(e)}")
    except Exception as e:
        raise Exception(f"调用失败: {str(e)}")

def search_messages(query):
    """搜索消息"""
    results = []
    for conv in st.session_state.conversations:
        for msg in conv["messages"]:
            if query.lower() in msg["content"].lower():
                results.append({
                    "conversation_id": conv["id"],
                    "title": conv["title"],
                    "content": msg["content"],
                    "role": msg["role"]
                })
    return results

def main():
    init_session_state()
    
    # 设置页面配置
    st.set_page_config(page_title="智能聊天助手", layout="wide")
    
    # 获取主题状态
    is_dark = st.session_state.get("dark_mode", False)
    
    # 自定义样式
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {'#0f0f0f' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'};
    }}
    .chat-container {{
        max-width: 800px;
        margin: 0 auto;
    }}
    .user-msg {{
        background-color: {'#1e40af' if is_dark else '#007bff'};
        color: #ffffff;
        border-radius: 16px;
        padding: 12px 16px;
        margin: 10px 0;
        max-width: 70%;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-size: 15px;
        line-height: 1.6;
    }}
    .assistant-msg {{
        background-color: {'#1f2937' if is_dark else '#f1f5f9'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border-radius: 16px;
        padding: 12px 16px;
        margin: 10px 0;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-size: 15px;
        line-height: 1.6;
    }}
    .msg-avatar {{
        font-size: 24px;
        margin-right: 8px;
    }}
    .stButton > button {{
        background-color: {'#374151' if is_dark else '#f0f2f6'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border: 1px solid {'#4b5563' if is_dark else '#e5e7eb'};
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        background-color: {'#4b5563' if is_dark else '#e5e7eb'};
    }}
    .stButton > button:active {{
        background-color: {'#6b7280' if is_dark else '#d1d5db'};
    }}
    .stTextInput > div > div > input {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border: 1px solid {'#374151' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    .stTextArea > div > div > textarea {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border: 1px solid {'#374151' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    .stSelectbox > div > div > select {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border: 1px solid {'#374151' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    [data-testid="stSidebar"] {{
        background-color: {'#1a1a2e' if is_dark else '#f8fafc'};
        padding: 16px 0;
    }}
    [data-testid="stSidebar"] .css-1d391kg {{
        background-color: {'#1a1a2e' if is_dark else '#f8fafc'};
    }}
    [data-testid="stSidebar"] * {{
        color: {'#f0f0f0' if is_dark else '#1f2937'} !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4 {{
        color: {'#ffffff' if is_dark else '#111827'} !important;
        font-weight: 600;
        margin-bottom: 12px;
    }}
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stTextArea > div > div > textarea,
    [data-testid="stSidebar"] .stSelectbox > div > div > select,
    [data-testid="stSidebar"] .stSelectbox > div > div > div > div {{
        background-color: {'#252542' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'} !important;
        border: 1px solid {'#3a3a5c' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div > div > div > div > div {{
        background-color: {'#252542' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'} !important;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div > div > div > div > div:hover {{
        background-color: {'#3a3a5c' if is_dark else '#f0f2f6'} !important;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div > div > svg {{
        color: {'#8888aa' if is_dark else '#6b7280'} !important;
    }}
    [data-testid="stSidebar"] .stSelectbox > div {{
        background-color: transparent !important;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background-color: transparent !important;
    }}
    [data-testid="stSidebar"] .stSelectbox > div > div > label {{
        color: {'#f0f0f0' if is_dark else '#1f2937'} !important;
        font-weight: 400 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        display: block !important;
    }}
    [data-testid="stSidebar"] .stTextInput > div > div > label,
    [data-testid="stSidebar"] .stTextArea > div > div > label {{
        color: {'#f0f0f0' if is_dark else '#1f2937'} !important;
        font-weight: 400 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        display: block !important;
    }}
    [data-testid="stSidebar"] .stButton > button {{
        background-color: {'#2d2d5a' if is_dark else '#f0f2f6'};
        color: {'#ffffff' if is_dark else '#1f2937'} !important;
        border: 1px solid {'#3a3a5c' if is_dark else '#e5e7eb'};
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: {'#3a3a5c' if is_dark else '#e5e7eb'};
    }}
    [data-testid="stSidebar"] .stToggle > div > div {{
        background-color: {'#252542' if is_dark else '#e5e7eb'};
    }}
    [data-testid="stSidebar"] .stToggle > div > div > div {{
        background-color: {'#4f46e5' if is_dark else '#007bff'};
    }}
    [data-testid="stSidebar"] .stSlider > div > div > div > div {{
        background-color: {'#252542' if is_dark else '#e5e7eb'};
    }}
    [data-testid="stSidebar"] .stSlider > div > div > div > div > div {{
        background-color: {'#4f46e5' if is_dark else '#007bff'};
    }}
    [data-testid="stSidebar"] .st-expander {{
        background-color: {'#252542' if is_dark else '#ffffff'};
        border: 1px solid {'#3a3a5c' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    [data-testid="stSidebar"] .css-16txtl3 {{
        border-bottom: 1px solid {'#252542' if is_dark else '#e5e7eb'};
    }}
    .stSlider > div > div > div > div {{
        background-color: {'#374151' if is_dark else '#e5e7eb'};
    }}
    .stSlider > div > div > div > div > div {{
        background-color: {'#3b82f6' if is_dark else '#007bff'};
    }}
    .st-expander {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
        border: 1px solid {'#374151' if is_dark else '#e5e7eb'};
        border-radius: 8px;
    }}
    .st-expander * {{
        color: {'#ffffff' if is_dark else '#1f2937'} !important;
    }}
    h1, h2, h3, h4, h5, h6, p, span, div, label {{
        color: {'#ffffff' if is_dark else '#1f2937'} !important;
    }}
    .stChatInput > div > div > input {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
        color: {'#ffffff' if is_dark else '#1f2937'};
        border: 1px solid {'#374151' if is_dark else '#e5e7eb'};
    }}
    .stSelectbox > div > div > div > div {{
        background-color: {'#1f2937' if is_dark else '#ffffff'};
    }}
    .stSelectbox > div > div > div > div > div {{
        color: {'#ffffff' if is_dark else '#1f2937'};
    }}
    .stToggle > div > div {{
        background-color: {'#1f2937' if is_dark else '#e5e7eb'};
    }}
    .stToggle > div > div > div {{
        background-color: {'#3b82f6' if is_dark else '#007bff'};
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.title("🤖 配置")
        
        # API配置
        st.subheader("API配置")
        st.session_state.api_key = st.text_input("API Key", value=st.session_state.api_key, type="password")
        st.session_state.base_url = st.text_input("Base URL", value=st.session_state.base_url)
        st.session_state.model = st.selectbox("模型", ["deepseek-v4-pro", "Claude-Opus-4.8"], index=0 if st.session_state.model == "deepseek-v4-pro" else 1)
        st.session_state.temperature = st.slider("温度", 0.0, 1.0, value=st.session_state.temperature, step=0.1)
        
        st.divider()
        
        # 聊天风格
        st.subheader("聊天风格")
        st.session_state.selected_style = st.selectbox("选择风格", list(STYLES.keys()), index=0)
        st.caption(STYLES[st.session_state.selected_style]["description"])
        
        # 自定义提示词
        st.session_state.custom_prompt = st.text_area("额外提示词", value=st.session_state.custom_prompt, height=80)
        
        st.divider()
        
        # 主题切换
        st.subheader("主题")
        dark_mode = st.toggle("暗色模式", value=is_dark)
        if dark_mode != is_dark:
            st.session_state.dark_mode = dark_mode
            st.rerun()
        
        # 头像显示设置
        st.session_state.show_avatar = st.toggle("显示头像", value=st.session_state.show_avatar)
        
        st.divider()
        
        # 搜索功能
        st.subheader("搜索记录")
        search_query = st.text_input("搜索关键词")
        if search_query:
            results = search_messages(search_query)
            if results:
                st.write(f"找到 {len(results)} 条结果")
                for idx, r in enumerate(results[:5]):
                    with st.expander(f"{r['title']}"):
                        st.write(f"**{r['role']}**: {r['content'][:100]}...")
                        if st.button("跳转", key=f"jump_{r['conversation_id']}_{idx}"):
                            # 从会话中查找完整对话
                            target_conv = next((c for c in st.session_state.conversations if c["id"] == r["conversation_id"]), None)
                            if target_conv:
                                select_conversation(target_conv)
                            st.rerun()
            else:
                st.write("未找到匹配结果")
    
    # 主聊天区域
    col1, col2 = st.columns([1, 3])
    
    # 左侧对话列表
    with col1:
        st.subheader("对话列表")
        if st.button("📝 新建对话", use_container_width=True):
            start_new_conversation()
        
        st.divider()
        
        # 显示对话列表
        for conv in reversed(st.session_state.conversations):
            is_selected = st.session_state.current_conversation == conv["id"]
            with st.container():
                col_left, col_right = st.columns([4, 1])
                with col_left:
                    if st.button(conv["title"], key=f"conv_{conv['id']}", use_container_width=True, 
                                type="primary" if is_selected else "secondary"):
                        select_conversation(conv)
                with col_right:
                    if st.button("🗑️", key=f"del_{conv['id']}", help="删除对话"):
                        delete_conversation(conv["id"])
                        st.rerun()
    
    # 右侧聊天窗口
    with col2:
        st.title("智能聊天助手")
        
        # 聊天容器
        chat_container = st.container()
        
        with chat_container:
            if st.session_state.current_conversation:
                # 显示消息
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        avatar_html = '<span class="msg-avatar">👤</span>' if st.session_state.show_avatar else ''
                        st.markdown(f"""
                        <div class="chat-container">
                            <div class="user-msg">
                                {avatar_html}
                                {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        avatar_html = '<span class="msg-avatar">🤖</span>' if st.session_state.show_avatar else ''
                        st.markdown(f"""
                        <div class="chat-container">
                            <div class="assistant-msg">
                                {avatar_html}
                                {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("请选择或创建一个对话开始聊天")
        
        # 输入区域
        if st.session_state.current_conversation:
            user_input = st.chat_input("输入消息...")
            
            if user_input:
                # 添加用户消息
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # 显示用户消息
                with chat_container:
                    avatar_html = '<span class="msg-avatar">👤</span>' if st.session_state.show_avatar else ''
                    st.markdown(f"""
                    <div class="chat-container">
                        <div class="user-msg">
                            {avatar_html}
                            {user_input}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 调用API
                with st.spinner("AI正在思考..."):
                    try:
                        response_text = ""
                        message_placeholder = st.empty()
                        avatar_html = '<span class="msg-avatar">🤖</span>' if st.session_state.show_avatar else ''
                        for chunk in call_llm_api(st.session_state.messages):
                            response_text += chunk
                            message_placeholder.markdown(f"""
                            <div class="chat-container">
                                <div class="assistant-msg">
                                    {avatar_html}
                                    {response_text}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # 添加助手消息
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                        
                        # 更新或保存对话
                        updated = False
                        for conv in st.session_state.conversations:
                            if conv["id"] == st.session_state.current_conversation:
                                conv["messages"] = st.session_state.messages
                                conv["title"] = generate_title(st.session_state.messages)
                                conv["updated_at"] = datetime.now().isoformat()
                                updated = True
                                break
                        
                        if not updated:
                            st.session_state.conversations.append({
                                "id": st.session_state.current_conversation,
                                "title": generate_title(st.session_state.messages),
                                "messages": st.session_state.messages,
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            })
                        
                        save_conversations()
                        
                    except Exception as e:
                        st.error(f"错误: {str(e)}")

if __name__ == "__main__":
    main()