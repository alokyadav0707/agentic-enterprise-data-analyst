"""Streamlit dashboard for the agentic data analyst."""
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
from src.config import DATABASE_PATH, LLM_MODE
from src.database.schema import create_database
from src.agent.workflow import AnalystAgent
from src.semantic_layer.catalog import load_catalog

st.set_page_config(page_title="Agentic Enterprise Data Analyst", page_icon="📊", layout="wide")
st.title("📊 Agentic Enterprise Data Analyst")
st.caption("OKF-inspired semantic layer • LangGraph workflow • guarded SQLite analytics")
if not DATABASE_PATH.exists():
    with st.spinner("Creating synthetic demo database..."):
        create_database(DATABASE_PATH)
mode = st.sidebar.selectbox("LLM mode", ["mock","groq"], index=0 if LLM_MODE=="mock" else 1,
                            help="Mock mode is deterministic. Groq mode requires GROQ_API_KEY.")
st.sidebar.info(f"Database: {DATABASE_PATH.name}")
examples = [
    "What are net sales?",
    "Show net sales by month",
    "Show the top 10 products by net sales",
    "What is the average order value?",
    "What percentage of customers placed at least two orders?",
    "Show order count and average order value by region",
    "Show gross profit by month",
]
selected = st.selectbox("Try an example question", ["(Choose one)"] + examples)
question = st.text_area("Ask a business question", value="" if selected=="(Choose one)" else selected,
                        placeholder="e.g. Show the top 10 products by net sales", height=90)
if st.button("Analyze", type="primary", disabled=not question.strip()):
    try:
        with st.spinner("Understanding question, retrieving metrics, generating and validating SQL..."):
            agent = AnalystAgent(mode=mode)
            result = agent.ask(question)
        status = "Success" if result["success"] else "Could not execute safely"
        st.subheader(status)
        c1,c2,c3 = st.columns(3)
        c1.metric("Attempts / retries", result["attempts"])
        c2.metric("Execution time", f'{result["latency_seconds"]:.2f}s')
        c3.metric("Mode", mode.upper())
        st.write(result["answer"])
        if result["semantic_context"]:
            st.caption("Retrieved metrics: " + ", ".join(result["semantic_context"]))
        with st.expander("Executed SQL", expanded=True):
            st.code(result["sql"] or "-- no SQL generated", language="sql")
        if result["error"]:
            st.warning(result["error"])
        if result["data"]:
            df = pd.DataFrame(result["data"])
            st.dataframe(df, use_container_width=True)
            numeric = df.select_dtypes(include="number").columns.tolist()
            categorical = [c for c in df.columns if c not in numeric]
            if numeric:
                if categorical:
                    x = categorical[0]
                    y = numeric[0]
                    if len(df) > 1:
                        st.plotly_chart(px.bar(df, x=x, y=y, title=f"{y} by {x}"), use_container_width=True)
                elif len(df) == 1:
                    cols = st.columns(min(len(numeric),4))
                    for i,col in enumerate(numeric[:4]):
                        cols[i].metric(col.replace("_"," ").title(), f"{df.iloc[0][col]:,.2f}")
                else:
                    st.plotly_chart(px.line(df, y=numeric[0], title=numeric[0]), use_container_width=True)
    except Exception as exc:
        st.error(f"Request failed: {exc}")

st.divider()
st.subheader("Semantic layer explorer")
catalog_path = Path(__file__).parent/"semantic_layer"/"metrics.yaml"
catalog = load_catalog(catalog_path)
for metric in catalog["metrics"]:
    with st.expander(f'{metric["name"]} — {metric["description"]}'):
        st.markdown(f'**Formula:** `{metric["expression"]}`')
        st.markdown(f'**Grain:** {metric["grain"]}')
        st.markdown(f'**Tables:** {", ".join(metric["tables"])}')
        st.markdown(f'**Business rules:** {metric["business_rules"]}')
