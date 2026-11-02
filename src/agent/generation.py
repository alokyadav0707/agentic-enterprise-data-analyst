"""LLM and deterministic mock SQL generation."""
import json
import re
from typing import Any

SCHEMA_HINT = """Tables:
customers(customer_id, customer_name, segment, region, signup_date, email_domain)
products(product_id, product_name, category, unit_cost, list_price)
orders(order_id, customer_id, order_date, status, channel)
order_items(order_item_id, order_id, product_id, quantity, unit_price, discount, unit_cost)
payments(payment_id, order_id, payment_date, payment_method, amount, payment_status)
returns(return_id, order_item_id, return_date, quantity, refund_amount, reason)
Rules: non-cancelled orders only for sales; net item sales = quantity*unit_price*(1-discount) minus returned refund_amount; never join raw payments and order_items before aggregation to avoid fan-out. Return only SQL, no markdown. SQLite dialect."""
def mock_generate(question: str) -> str:
    q = question.lower()
    if "top" in q and "product" in q:
        n = re.search(r"top\s+(\d+)", q)
        limit = int(n.group(1)) if n else 10
        return f"""SELECT p.product_name, ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)),2) AS net_sales
FROM products p JOIN order_items oi ON oi.product_id=p.product_id
JOIN orders o ON o.order_id=oi.order_id LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY p.product_id,p.product_name ORDER BY net_sales DESC LIMIT {min(limit,100)}"""
    if "by month" in q and ("sales" in q or "revenue" in q):
        return """SELECT strftime('%Y-%m',o.order_date) AS month,
ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)),2) AS net_sales
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY month ORDER BY month"""
    if "average order value" in q or "aov" in q:
        return """WITH order_sales AS (
SELECT o.order_id, SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)) AS sales
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY o.order_id)
SELECT ROUND(AVG(sales),2) AS average_order_value FROM order_sales"""
    if "repeat customer" in q or "at least two orders" in q or "repeat customer rate" in q:
        return """WITH counts AS (
SELECT customer_id, COUNT(*) AS n FROM orders WHERE status <> 'cancelled' GROUP BY customer_id)
SELECT ROUND(100.0*SUM(CASE WHEN n>=2 THEN 1 ELSE 0 END)/COUNT(*),2) AS repeat_customer_rate_pct FROM counts"""
    if "order count" in q and ("region" in q or "segment" in q):
        dim = "c.region" if "region" in q else "c.segment"
        alias = "region" if "region" in q else "segment"
        return f"""SELECT {dim} AS {alias}, COUNT(DISTINCT o.order_id) AS order_count,
ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0))/COUNT(DISTINCT o.order_id),2) AS average_order_value
FROM customers c JOIN orders o ON o.customer_id=c.customer_id
JOIN order_items oi ON oi.order_id=o.order_id LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY {dim} ORDER BY order_count DESC"""
    if "gross profit" in q and "month" in q:
        return """SELECT strftime('%Y-%m',o.order_date) AS month,
ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)-oi.quantity*oi.unit_cost),2) AS gross_profit
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY month ORDER BY month"""
    if "customer lifetime value" in q or "clv" in q or "top customers" in q:
        return """SELECT c.customer_id,c.customer_name,
ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)),2) AS customer_lifetime_value
FROM customers c JOIN orders o ON o.customer_id=c.customer_id
JOIN order_items oi ON oi.order_id=o.order_id LEFT JOIN returns r ON r.order_item_id=oi.order_item_id
WHERE o.status <> 'cancelled' GROUP BY c.customer_id,c.customer_name
ORDER BY customer_lifetime_value DESC LIMIT 10"""
    if "sales" in q or "revenue" in q or "net sales" in q:
        return """SELECT ROUND(SUM(oi.quantity*oi.unit_price*(1-oi.discount)-COALESCE(r.refund_amount,0)),2) AS net_sales
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
LEFT JOIN returns r ON r.order_item_id=oi.order_item_id WHERE o.status <> 'cancelled'"""
    if "customer" in q and ("region" in q or "segment" in q):
        dim = "region" if "region" in q else "segment"
        return f"SELECT {dim}, COUNT(*) AS customer_count FROM customers GROUP BY {dim} ORDER BY customer_count DESC"
    # Deliberate transparent fallback: fail rather than fabricate an answer.
    return "SELECT unsupported_question_pattern AS error"

def generate_sql(question: str, semantic_context: list[dict], mode: str = "mock", model_name: str = "") -> str:
    """Generate SQL using configured LLM or deterministic mock templates."""
    if mode == "mock":
        return mock_generate(question)
    if mode != "groq":
        raise ValueError(f"Unknown LLM_MODE: {mode}")
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage
    import os
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_MODE=groq but GROQ_API_KEY is not set")
    llm = ChatGroq(model=model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                   temperature=0, api_key=api_key)
    metrics = json.dumps(semantic_context, ensure_ascii=False)
    prompt = f"""You are a careful SQLite analytics engineer. Generate one read-only SELECT query.
{SCHEMA_HINT}
Semantic metric definitions retrieved for this question:
{metrics}
Question: {question}
Return only SQL. Do not use unknown tables/columns. Do not use SELECT * unless useful.
"""
    response = llm.invoke([SystemMessage(content="Return valid SQLite SQL only."), HumanMessage(content=prompt)])
    sql = str(response.content).strip()
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.I)
    return sql
