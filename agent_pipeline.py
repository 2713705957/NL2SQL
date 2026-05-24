from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

class SQLGradingState(TypedDict):
    """SQL 生成流水线状态"""
    user_question: str
    table_schema: dict
    generated_sql: str


llm = ChatOpenAI(
    model="kimi-k2.6",              
    api_key="sk-UxUGtzMoxteqxA748vLW7gQta1jk7R8br5Und36RH9Qo05bD",
    base_url="https://api.moonshot.cn/v1",
    temperature=1
)



def _build_schema_text(table_schema: dict) -> str:
    """将表结构转换为文本描述。"""
    if not table_schema:
        return ""
    name = table_schema.get("name", "table_name")
    cols = table_schema.get("columns", [])
    lines = [f"表名：{name}"]
    lines.append("列信息：")
    for i, col in enumerate(cols):
        lines.append(f"  - col_{i+1}（中文含义：{col}）")
    return "\n".join(lines)


def parsing_agent(state: SQLGradingState) -> dict:
    """解析Agent：解析用户的自然语言问题，提取关键信息"""
    print("[解析Agent] 正在解析用户问题...")

    schema_text = _build_schema_text(state.get("table_schema", {}))

    prompt = f"""\
你是一个SQL问题解析专家。请仔细分析用户的自然语言问题，提取以下信息：
1. 查询目标（想要获取什么数据）
2. 涉及的表名和字段
3. 查询条件
4. 排序要求
5. 聚合函数需求

{schema_text}

用户问题：{state['user_question']}

请用简洁的JSON格式返回解析结果，不需要额外解释。
"""

    response = llm.invoke(prompt)
    try:
        import json, re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            parsed_data = json.loads(json_match.group())
        else:
            parsed_data = {"raw_analysis": response.content}
    except Exception:
        parsed_data = {"raw_analysis": response.content}

    return {"parsed_question": parsed_data}


def sql_generation_agent(state: SQLGradingState) -> dict:
    """SQL生成Agent：根据解析结果和表结构生成SQL查询"""
    print("[SQL生成Agent] 正在生成SQL查询...")

    schema_text = _build_schema_text(state.get("table_schema", {}))

    prompt = f"""\
你是一个SQL专家。基于以下表结构和问题解析结果，生成一个正确的SQLite SQL查询语句。

{schema_text}

用户原始问题：{state['user_question']}

解析结果：{state.get('parsed_question', {})}

要求：
1. 只输出SQL语句，不要有任何额外说明或注释
2. 必须使用数据库实际列名（col_1, col_2等）
3. 字符串值需要加单引号
4. 表名使用：{state.get('table_schema', {}).get('name', 'table_name')}

SQL："""

    response = llm.invoke(prompt)
    sql = response.content.strip()
    sql = sql.replace('```sql', '').replace('```', '').strip()

    return {"generated_sql": sql}


# 构建简化的生成流水线
def create_sql_grading_agent():
    """创建SQL生成Agent流水线（仅解析+生成）"""
    graph = StateGraph(SQLGradingState)

    graph.add_node("parse", parsing_agent)
    graph.add_node("generate", sql_generation_agent)

    graph.add_edge(START, "parse")
    graph.add_edge("parse", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# 运行SQL生成
def run_sql_grading(user_question: str, table_schema: dict = None) -> dict:
    """根据自然语言问题生成SQL。若提供table_schema，LLM会基于真实表结构生成。"""
    agent = create_sql_grading_agent()

    initial_state: SQLGradingState = {
        "user_question": user_question,
        "table_schema": table_schema or {},
        "generated_sql": "",
    }

    result = agent.invoke(initial_state)
    return {
        "generated_sql": result.get("generated_sql", ""),
        "final_grade": "生成完成",
    }

# ==================== 新增：判题流水线 ====================

from typing import TypedDict
from nl2sql_loader import load_question_by_id, TRAIN_DB, get_table_schema
from judge_core import (
    safe_execute_sql,
    compare_results,
    extract_sql_features,
    semantic_equivalence_check,
    generate_educational_feedback,
)


class JudgeState(TypedDict):
    """判题流水线状态定义"""
    question_id: int
    question_text: str
    table_schema: dict
    standard_sql: str
    standard_sql_features: dict
    user_sql: str
    execution_result: dict
    comparison_result: dict
    equivalence_result: dict
    final_report: dict


def load_question_node(state: JudgeState) -> dict:
    """加载题目、标准答案及特征"""
    qid = state["question_id"]
    try:
        qinfo = load_question_by_id(qid)
    except IndexError as e:
        return {
            "question_text": f"题目加载失败：{e}",
            "table_schema": {},
            "standard_sql": "",
            "standard_sql_features": {},
        }

    std_sql = qinfo["standard_sql"].replace("table_name", f"`{qinfo['table_schema']['name']}`")
    features = extract_sql_features(std_sql, qinfo["table_schema"])

    return {
        "question_text": qinfo["question"],
        "table_schema": qinfo["table_schema"],
        "standard_sql": std_sql,
        "standard_sql_features": features,
    }


def execute_node(state: JudgeState) -> dict:
    """执行用户 SQL"""
    user_sql = state["user_sql"]
    ok, result, columns = safe_execute_sql(user_sql, TRAIN_DB, timeout=5)

    return {
        "execution_result": {
            "success": ok,
            "rows": result if ok else [],
            "columns": columns if ok else [],
            "error_msg": "" if ok else str(result),
        }
    }


def compare_node(state: JudgeState) -> dict:
    """比对用户结果与标准结果"""
    user_exec = state["execution_result"]
    if not user_exec.get("success"):
        return {
            "comparison_result": {
                "match": False,
                "diff": "用户 SQL 执行失败，无法比对结果。",
                "user_count": 0,
                "standard_count": 0,
            }
        }

    # 执行标准 SQL 获取标准结果
    std_sql = state["standard_sql"]
    ok_std, std_rows, _ = safe_execute_sql(std_sql, TRAIN_DB, timeout=5)
    if not ok_std:
        return {
            "comparison_result": {
                "match": False,
                "diff": f"标准 SQL 执行失败：{std_rows}",
                "user_count": len(user_exec.get("rows", [])),
                "standard_count": 0,
            }
        }

    cmp = compare_results(user_exec["rows"], std_rows)
    return {"comparison_result": cmp}


def semantic_node(state: JudgeState) -> dict:
    """调用语义等价判断（仅在结果比对不完全一致时调用）"""
    if state["comparison_result"].get("match"):
        return {
            "equivalence_result": {
                "equiv": True,
                "reason": "结果集已完全一致，无需额外语义判断。",
                "raw": "",
            }
        }

    sem = semantic_equivalence_check(
        question=state["question_text"],
        user_sql=state["user_sql"],
        standard_sql_features=state["standard_sql_features"],
        table_schema=state["table_schema"],
    )
    return {"equivalence_result": sem}


def feedback_node(state: JudgeState) -> dict:
    """生成最终判题报告"""
    exec_res = state["execution_result"]
    cmp_res = state["comparison_result"]
    eq_res = state["equivalence_result"]

    error_info = {
        "has_error": not exec_res.get("success", False),
        "error_msg": exec_res.get("error_msg", ""),
        "table_schema": state["table_schema"],
    }

    # 判断最终状态
    if exec_res.get("success") and cmp_res.get("match"):
        status = "correct"
    elif eq_res.get("equiv"):
        status = "partial"
    else:
        status = "incorrect"

    # 生成教学反馈
    fb = generate_educational_feedback(
        question=state["question_text"],
        user_sql=state["user_sql"],
        error_info=error_info,
        similarity_result=cmp_res,
    )

    # 如果完全正确，覆盖反馈为鼓励
    if status == "correct":
        fb["status"] = "correct"
        fb["summary"] = "你的 SQL 完全正确！逻辑和结果都与标准答案一致。"

    report = {
        "status": status,
        "execution_result": {
            "success": exec_res.get("success"),
            "columns": exec_res.get("columns", []),
            "rows": exec_res.get("rows", []),
            "error_msg": exec_res.get("error_msg", ""),
        },
        "comparison": cmp_res,
        "semantic_analysis": eq_res,
        "error_location": fb.get("summary", ""),
        "feedback": fb.get("suggestion", ""),
        "knowledge_point": fb.get("knowledge_point", ""),
    }

    return {"final_report": report}


# 构建判题流水线
def create_judge_agent():
    """创建判题 Agent 流水线"""
    graph = StateGraph(JudgeState)

    graph.add_node("load_question", load_question_node)
    graph.add_node("execute", execute_node)
    graph.add_node("compare", compare_node)
    graph.add_node("semantic", semantic_node)
    graph.add_node("feedback", feedback_node)

    graph.add_edge(START, "load_question")
    graph.add_edge("load_question", "execute")
    graph.add_edge("execute", "compare")
    graph.add_edge("compare", "semantic")
    graph.add_edge("semantic", "feedback")
    graph.add_edge("feedback", END)

    return graph.compile()


def run_judge(question_id: int, user_sql: str) -> dict:
    """
    执行整个判题流水线，返回最终报告 JSON。
    """
    agent = create_judge_agent()

    initial_state: JudgeState = {
        "question_id": question_id,
        "question_text": "",
        "table_schema": {},
        "standard_sql": "",
        "standard_sql_features": {},
        "user_sql": user_sql,
        "execution_result": {},
        "comparison_result": {},
        "equivalence_result": {},
        "final_report": {},
    }

    result = agent.invoke(initial_state)
    return result["final_report"]


# ==================== 测试入口 ====================
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("新增判题流水线测试（题目1，使用标准SQL作为用户输入）")
    print("=" * 60)

    # 先获取标准 SQL
    qinfo = load_question_by_id(0)
    std_sql = qinfo["standard_sql"].replace("table_name", f"`{qinfo['table_schema']['name']}`")
    print(f"题目：{qinfo['question']}")
    print(f"用户SQL：{std_sql}")

    judge_result = run_judge(0, std_sql)
    print(f"\n判题报告：")
    print(json.dumps(judge_result, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("原有生成流水线测试（需要 Ollama 服务）")
    print("=" * 60)
    try:
        test_question = "查询年龄大于18岁的学生姓名和成绩"
        result = run_sql_grading(test_question)
        print(f"最终得分：{result['final_grade']}")
        print(f"生成的SQL：{result['generated_sql']}")
    except Exception as e:
        print(f"原流水线测试跳过（Ollama 未启动）：{e}")


