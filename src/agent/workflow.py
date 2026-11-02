"""LangGraph-based agentic NL-to-SQL workflow with bounded correction."""
from __future__ import annotations
import time
from typing import TypedDict, Any
from pathlib import Path
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    StateGraph = None
    END = "__end__"
from src.config import DATABASE_PATH, LLM_MODE, GROQ_MODEL, MAX_CORRECTION_ATTEMPTS
from src.semantic_layer.catalog import load_catalog, retrieve_relevant
from src.agent.generation import generate_sql
from src.agent.validation import validate_sql, SQLValidationError
from src.database.executor import execute_sql
from src.database.schema import DDL

class AgentState(TypedDict, total=False):
    question: str
    semantic_context: list[dict]
    sql: str
    dataframe: Any
    error: str
    attempts: int
    max_attempts: int
    success: bool
    answer: str
    started: float
    mode: str
    correction_enabled: bool

class AnalystAgent:
    def __init__(self, db_path=DATABASE_PATH, catalog_path=None, mode=None, correction_enabled=True):
        self.db_path = Path(db_path)
        self.catalog_path = Path(catalog_path or Path(__file__).resolve().parents[2] / "semantic_layer" / "metrics.yaml")
        self.catalog = load_catalog(self.catalog_path)
        self.mode = mode or LLM_MODE
        self.correction_enabled = correction_enabled
        self.graph = self._build_graph() if StateGraph else None

    def _understand(self, state):
        q = state["question"].strip()
        return {"question": q, "error": "", "attempts": 0, "max_attempts": MAX_CORRECTION_ATTEMPTS,
                "started": time.perf_counter(), "mode": self.mode, "correction_enabled": self.correction_enabled}

    def _retrieve(self, state):
        return {"semantic_context": retrieve_relevant(state["question"], self.catalog)}

    def _generate(self, state):
        sql = generate_sql(state["question"], state.get("semantic_context", []), state["mode"], GROQ_MODEL)
        return {"sql": sql, "error": ""}

    def _validate(self, state):
        try:
            sql = validate_sql(state["sql"], {"customers","products","orders","order_items","payments","returns"})
            return {"sql": sql, "error": ""}
        except Exception as exc:
            return {"error": f"Validation error: {exc}"}

    def _execute(self, state):
        try:
            df = execute_sql(state["sql"], self.db_path)
            if "error" in df.columns:
                raise ValueError("Generated SQL refers to an unsupported question pattern")
            return {"dataframe": df, "success": True, "error": ""}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _correct(self, state):
        # Correction is a bounded regeneration with the error included in the question context.
        attempts = state.get("attempts", 0) + 1
        if attempts >= state.get("max_attempts", 3):
            return {"attempts": attempts}
        corrected_question = (state["question"] + "\nPrevious SQL failed with error: " + state.get("error", "") +
                              "\nFix the SQL while preserving the original business question.")
        try:
            sql = generate_sql(corrected_question, state.get("semantic_context", []), state["mode"], GROQ_MODEL)
            return {"sql": sql, "attempts": attempts, "error": ""}
        except Exception as exc:
            return {"attempts": attempts, "error": str(exc)}

    def _answer(self, state):
        df = state.get("dataframe")
        if df is None:
            return {"answer": "I could not safely execute a query for this question. Review the SQL/error details and try a more specific question."}
        if df.empty:
            answer = "The query ran successfully but returned no rows."
        elif len(df) == 1 and len(df.columns) == 1:
            answer = f"Result: **{df.iloc[0,0]}**."
        else:
            answer = f"Query succeeded and returned {len(df)} row(s) across {len(df.columns)} column(s)."
        return {"answer": answer}

    def _route_after_validation(self, state):
        if state.get("error"):
            return "correct" if state.get("correction_enabled") and state.get("attempts",0) < state.get("max_attempts",3) else "answer"
        return "execute"

    def _route_after_execute(self, state):
        if state.get("success"):
            return "answer"
        return "correct" if state.get("correction_enabled") and state.get("attempts",0) < state.get("max_attempts",3) else "answer"

    def _route_after_correct(self, state):
        # _correct has already regenerated SQL; validate that SQL rather than overwriting it.
        return "validate" if state.get("attempts",0) < state.get("max_attempts",3) and not state.get("error") else "answer"

    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("understand", self._understand)
        g.add_node("retrieve", self._retrieve)
        g.add_node("generate", self._generate)
        g.add_node("validate", self._validate)
        g.add_node("execute", self._execute)
        g.add_node("correct", self._correct)
        g.add_node("answer", self._answer)
        g.set_entry_point("understand")
        g.add_edge("understand","retrieve")
        g.add_edge("retrieve","generate")
        g.add_edge("generate","validate")
        g.add_conditional_edges("validate", self._route_after_validation, {"execute":"execute","correct":"correct","answer":"answer"})
        g.add_conditional_edges("execute", self._route_after_execute, {"answer":"answer","correct":"correct"})
        g.add_conditional_edges("correct", self._route_after_correct, {"validate":"validate","answer":"answer"})
        g.add_edge("answer", END)
        return g.compile()

    def ask(self, question: str) -> dict:
        """Run the workflow and return a JSON-friendly response."""
        initial = {"question": question, "mode": self.mode, "correction_enabled": self.correction_enabled}
        if self.graph:
            result = self.graph.invoke(initial)
        else:
            # Minimal fallback for environments without LangGraph installed.
            state = self._understand(initial)
            state.update(self._retrieve(state))
            while True:
                try:
                    state.update(self._generate(state)); state.update(self._validate(state))
                    if state.get("error"): raise SQLValidationError(state["error"])
                    state.update(self._execute(state))
                    if state.get("success"): break
                    raise RuntimeError(state.get("error","execution failed"))
                except Exception as exc:
                    state["error"] = str(exc)
                    if not self.correction_enabled or state.get("attempts",0) >= state.get("max_attempts",3): break
                    state.update(self._correct(state))
                    if state.get("attempts",0) >= state.get("max_attempts",3): break
            state.update(self._answer(state)); result = state
        df = result.get("dataframe")
        return {"question": question, "sql": result.get("sql",""), "answer": result.get("answer",""),
                "success": bool(result.get("success",False)), "error": result.get("error",""),
                "attempts": int(result.get("attempts",0)), "latency_seconds": round(time.perf_counter()-result.get("started",time.perf_counter()),4),
                "data": df.to_dict(orient="records") if df is not None else [],
                "columns": list(df.columns) if df is not None else [],
                "semantic_context": [m["name"] for m in result.get("semantic_context",[])]}
