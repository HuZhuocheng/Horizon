import streamlit as st
import pandas as pd
from agent.core import CreditRiskAgent

st.set_page_config(page_title="Horizon — 风险洞察助手", page_icon="🏦", layout="wide")

# 初始化 session state
if "report_generated" not in st.session_state:
    st.session_state.report_generated = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "agent" not in st.session_state:
    st.session_state.agent = CreditRiskAgent()

st.title("🏦 Horizon — 企业经营风险洞察助手")
st.markdown("""
> **核心定位**：人做最终决策，Agent 做资料整理、指标提取、规则校验、风险提示辅助。
""")

# 左侧边栏：任务配置与文件上传
with st.sidebar:
    st.header("⚙️ 大模型 (LLM) 配置")
    st.markdown("配置后可体验真实的智能多轮对话分析。若不配置，将默认使用本地 Mock 数据演示。")
    
    with st.expander("API 设置 (可选)", expanded=False):
        api_key = st.text_input("API Key", type="password", placeholder="例如: sk-...")
        base_url = st.text_input("Base URL", placeholder="例如: https://dashscope.aliyuncs.com/compatible-mode/v1")
        model_name = st.text_input("Model", value="qwen-plus")
        
        if st.button("保存 LLM 配置"):
            st.session_state.agent.update_llm_config(
                api_key=api_key if api_key else None,
                base_url=base_url if base_url else None,
                model=model_name
            )
            if api_key:
                st.success("✅ LLM 配置已更新并启用！")
            else:
                st.info("ℹ️ 已切换回 Mock 演示模式。")

    st.divider()

    st.header("📂 任务配置区")
    st.markdown("上传企业尽调材料（财报、工商报告、司法文书等）")
    uploaded_files = st.file_uploader("选择文件（PDF/扫描件/图片）", accept_multiple_files=True)
    
    instruction = st.text_area("下达尽调指令", value="对 XX 有限公司做信贷前置尽调，输出风险简报")
    
    start_btn = st.button("🚀 开始自动化尽调", type="primary")
    
    st.divider()
    st.markdown("### � 快速体验 (免 API)")
    st.markdown("没有文件？您可以下载下方示例文件并上传，或直接点击一键运行体验内置流程。")
    try:
        with open("mock_data/示例企业尽调材料.txt", "r", encoding="utf-8") as f:
            sample_content = f.read()
        st.download_button("📥 下载示例材料", data=sample_content, file_name="示例企业尽调材料.txt")
    except Exception as e:
        pass
        
    run_sample_btn = st.button("⚡ 一键运行内置示例", type="secondary")

    st.divider()
    st.markdown("### �📋 可配置风控规则库 (部分展示)")
    rules_df = pd.DataFrame(st.session_state.agent.rules)
    st.dataframe(rules_df[['id', 'name', 'risk_level']])

# 主区域展示
if start_btn or run_sample_btn:
    if run_sample_btn:
        uploaded_files = ["内置示例企业尽调材料.txt"]
        
    if not uploaded_files:
        st.warning("⚠️ 请先上传至少一份企业材料进行 Demo 演示（可随意上传任意文件模拟）。")
    else:
        if run_sample_btn:
            st.info("ℹ️ 已自动加载内置示例材料进行分析。")
            
        st.session_state.report_generated = False
        st.session_state.chat_history = []
        
        # 进度展示
        with st.status("Agent 正在执行工作流编排...", expanded=True) as status:
            st.write("📄 子任务 1：多模态文档解析，提取经营指标、涉诉、工商信息...")
            st.session_state.extracted_data = st.session_state.agent.parse_documents(uploaded_files)
            
            st.write("🔍 子任务 2 & 3：调用风控规则知识库做规则匹配...")
            risk_results = st.session_state.agent.run_rule_engine(st.session_state.extracted_data)
            
            st.write("📝 子任务 4：风险标记与整理，生成尽调简报...")
            report_md = st.session_state.agent.generate_report(st.session_state.extracted_data, risk_results)
            
            status.update(label="✅ 尽调任务执行完成！", state="complete", expanded=False)
            
        st.session_state.report_md = report_md
        st.session_state.report_generated = True

if st.session_state.report_generated:
    col1, col2 = st.columns([6, 4])
    
    with col1:
        st.subheader("📑 结构化尽调简报")
        st.markdown(st.session_state.report_md)
        st.download_button(
            label="📥 导出为 Markdown 报告",
            data=st.session_state.report_md,
            file_name="horizon_risk_report.md",
            mime="text/markdown"
        )
        
    with col2:
        st.subheader("💬 多轮交互与追问")
        
        mode_text = "🟢 **真实 LLM 模式**" if st.session_state.agent.client else "🟠 **Mock 演示模式** (可在左侧边栏配置 API Key 切换)"
        st.markdown(f"当前模式：{mode_text}")
        st.markdown("您可以对底层材料进行追问，如：*“这家公司的资产负债率是否健康？”* 或 *“帮我总结一下该公司的风险点”*")
        
        st.markdown("**💡 快捷追问示例：**")
        example_cols = st.columns(3)
        with example_cols[0]:
            ex1 = st.button("涉诉案件详细情况？", use_container_width=True)
        with example_cols[1]:
            ex2 = st.button("过滤已结案诉讼", use_container_width=True)
        with example_cols[2]:
            ex3 = st.button("重新核算流动比率", use_container_width=True)
        
        # 显示聊天记录
        for msg in st.session_state.chat_history:
            role = "🧑‍💼 业务员" if msg["role"] == "user" else "🤖 Horizon Agent"
            st.markdown(f"**{role}**: {msg['content']}")
            
        # 聊天输入
        query = st.chat_input("输入您的追问指令...")
        
        active_query = query
        if ex1: active_query = "这条涉诉案件详细内容是什么？"
        if ex2: active_query = "过滤掉已结案诉讼"
        if ex3: active_query = "重新核算该企业流动比率"
        
        if active_query:
            # 记录用户问题
            st.session_state.chat_history.append({"role": "user", "content": active_query})
            
            # Agent 响应
            with st.spinner("Horizon 正在分析..."):
                reply = st.session_state.agent.handle_query(active_query, st.session_state.extracted_data)
                st.session_state.chat_history.append({"role": "agent", "content": reply})
                st.rerun()
