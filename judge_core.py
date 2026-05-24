"""
judge_core.py
判题核心模块：安全执行、结果比对、语义等价判断、教学反馈生成。
"""

import json
import sqlite3
import re
from typing import Any

from langchain_openai import ChatOpenAI

from nl2sql_loader import get_db_connection

llm = ChatOpenAI(
    model="kimi-k2.6",              
    api_key="sk-UxUGtzMoxteqxA748vLW7gQta1jk7R8br5Und36RH9Qo05bD",
    base_url="https://api.moonshot.cn/v1",
    temperature=1
)

# ---------- 安全执行 ----------

FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]


def safe_execute_sql(sql: str, db_path: str, timeout: int = 5) -> tuple[bool, Any, list[str] | None]:
    """
    在 SQLite 中执行 SQL，返回 (success, result/error_msg, columns)。

    - 先检查是否包含危险关键字
    - 设置执行超时
    - 返回结果集或错误信息
    """
    # 安全检查
    upper_sql = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in upper_sql:
            return False, f"安全拦截：SQL 中包含禁用关键字 '{keyword}'", None

    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        conn.execute("PRAGMA busy_timeout = 5000")
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.description is None:
            # 无结果集的语句（如被绕过的 DDL）
            conn.close()
            return False, "执行结果为空或无返回数据", None

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return True, rows, columns
    except Exception as e:
        return False, f"执行错误：{str(e)}", None


# ---------- 结果集比对 ----------


def compare_results(user_results: list[Any], standard_results: list[Any]) -> dict[str, Any]:
    """
    比对两个结果集（先排序），返回 {match: bool, diff: str, user_count: int, standard_count: int}。
    """
    # 排序：将所有元素转为可排序的字符串表示进行排序
    def sort_key(row):
        if row is None:
            return ""
        if isinstance(row, (list, tuple)):
            return json.dumps([str(c) for c in row], ensure_ascii=False)
        return str(row)

    sorted_user = sorted(user_results, key=sort_key)
    sorted_std = sorted(standard_results, key=sort_key)

    match = sorted_user == sorted_std

    diff_parts = []
    if not match:
        diff_parts.append(f"结果行数不同：用户 {len(user_results)} 行，标准 {len(standard_results)} 行")
        # 尝试找出差异样本
        min_len = min(len(sorted_user), len(sorted_std))
        for i in range(min_len):
            if sorted_user[i] != sorted_std[i]:
                diff_parts.append(f"第 {i+1} 行不同：用户 {sorted_user[i]} vs 标准 {sorted_std[i]}")
                if i >= 2:
                    break
        if len(sorted_user) != len(sorted_std):
            diff_parts.append("行数不一致，可能是遗漏或多余了数据。")
    else:
        diff_parts.append("结果集完全一致（排序后比对）。")

    return {
        "match": match,
        "diff": "\n".join(diff_parts),
        "user_count": len(user_results),
        "standard_count": len(standard_results),
    }


# ---------- 特征提取 ----------


def extract_sql_features(sql: str, table_schema: dict[str, Any]) -> dict[str, Any]:
    """
    提取 SQL 的关键特征：涉及的表、查询类型、聚合、条件列等。
    返回特征字典，用于语义等价判断，不泄露完整 SQL。
    """
    upper = sql.upper()
    features: dict[str, Any] = {
        "tables": [table_schema.get("name", "")],
        "query_type": "SELECT",
        "aggregations": [],
        "condition_columns": [],
        "has_where": "WHERE" in upper,
        "has_group_by": "GROUP BY" in upper,
        "has_order_by": "ORDER BY" in upper,
        "has_join": "JOIN" in upper,
    }

    # 提取聚合函数
    agg_pattern = re.compile(r"\b(AVG|SUM|COUNT|MAX|MIN)\s*\(", re.IGNORECASE)
    features["aggregations"] = list(set(m.group(1).upper() for m in agg_pattern.finditer(sql)))

    # 提取 WHERE 条件涉及的列名（简单正则）
    where_match = re.search(r"WHERE\s+(.+?)(?:ORDER BY|GROUP BY|LIMIT|$)", sql, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1)
        # 匹配 col_name op value 模式
        col_pattern = re.compile(r"`?(\w+)`?\s*[=<>!]+", re.IGNORECASE)
        features["condition_columns"] = list(set(col_pattern.findall(where_clause)))

    return features


# ---------- 语义等价判断 ----------

SEMANTIC_EQUIVALENCE_PROMPT = """\
你是一位SQL专家。请判断用户提交的SQL是否与题目要求逻辑等价。

题目：{question}
表结构：{table_schema}
用户SQL：{user_sql}

标准答案的特征（不是完整SQL）：
- 涉及的表：{tables}
- 查询类型：{query_type}
- 使用的聚合函数：{aggregations}
- 条件涉及的列：{condition_columns}

判断标准：只要逻辑结果与上述特征一致，即使写法不同（如 JOIN 与子查询互换），也应判定为等价。
请返回JSON：{{"equiv": true/false, "reason": "..."}}
"""


def semantic_equivalence_check(
    question: str,
    user_sql: str,
    standard_sql_features: dict[str, Any],
    table_schema: dict[str, Any],
) -> dict[str, Any]:
    """
    使用 LLM 判断逻辑等价性。
    standard_sql_features 是标准答案的抽象特征，不是完整 SQL！
    """
    prompt = SEMANTIC_EQUIVALENCE_PROMPT.format(
        question=question,
        table_schema=json.dumps(table_schema, ensure_ascii=False),
        user_sql=user_sql,
        tables=standard_sql_features.get("tables", []),
        query_type=standard_sql_features.get("query_type", "SELECT"),
        aggregations=standard_sql_features.get("aggregations", []),
        condition_columns=standard_sql_features.get("condition_columns", []),
    )

    try:
        response = llm.invoke(prompt)
        content = response.content
        # 尝试提取 JSON
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "equiv": bool(result.get("equiv", False)),
                "reason": result.get("reason", ""),
                "raw": content,
            }
        else:
            return {"equiv": False, "reason": "无法解析模型返回的 JSON", "raw": content}
    except Exception as e:
        return {"equiv": False, "reason": f"模型调用失败：{str(e)}", "raw": ""}


# ---------- 追问教学反馈生成 ----------

EDUCATIONAL_FEEDBACK_PROMPT = """\
你是一位耐心、鼓励的SQL教学助教。学生在做一道SQL练习题。

题目：{question}
表结构：{table_schema}
学生提交的SQL：{user_sql}
执行结果：{execution_error}
比对差异：{comparison_diff}

请用引导式语言给予反馈：
1. 指出错误的具体位置（哪个子句、哪一行）
2. 用通俗比喻解释为什么这样是错的
3. 给出修改提示（但不要给完整正确答案）
4. 推荐一个相关的SQL知识点供学生复习
5. 语气友好，使用"你"称呼
"""


def generate_educational_feedback(
    question: str,
    user_sql: str,
    error_info: dict[str, Any],
    similarity_result: dict[str, Any],
) -> dict[str, Any]:
    """
    根据错误类型生成引导式反馈，不直接给出完整答案。
    """
    execution_error = error_info.get("error_msg", "执行成功")
    comparison_diff = similarity_result.get("diff", "")

    # 如果结果完全正确，给出鼓励
    if similarity_result.get("match") and not error_info.get("has_error"):
        return {
            "status": "correct",
            "summary": "你的 SQL 完全正确！逻辑和结果都与标准答案一致。",
            "suggestion": "可以尝试思考是否有更高效的写法，或者不同的实现思路。",
            "knowledge_point": "SQL 优化与执行计划基础",
            "raw_feedback": "",
        }

    prompt = EDUCATIONAL_FEEDBACK_PROMPT.format(
        question=question,
        table_schema=json.dumps(error_info.get("table_schema", {}), ensure_ascii=False),
        user_sql=user_sql,
        execution_error=execution_error,
        comparison_diff=comparison_diff,
    )

    try:
        response = llm.invoke(prompt)
        content = response.content
    except Exception as e:
        content = f"生成反馈时出错：{str(e)}"

    # 简单提取摘要（取第一行或前 50 字）
    summary = content.split("\n")[0][:80] if content else "请查看详细反馈"

    return {
        "status": "partial" if similarity_result.get("user_count") else "incorrect",
        "summary": summary,
        "suggestion": content,
        "knowledge_point": "",
        "raw_feedback": content,
    }


# ---------- 追问功能 Prompt ----------

FOLLOW_UP_PROMPT = """\
基于以下参考知识库内容回答学生的追问。

参考知识：
{context}

题目描述：{question}
学生当前SQL：{user_sql}
之前判题反馈：{previous_feedback}

学生追问：{follow_up_question}

请用中文回答，保持教学引导风格。
"""


def build_follow_up_prompt(
    context: str,
    question: str,
    user_sql: str,
    previous_feedback: str,
    follow_up_question: str,
) -> str:
    """构建追问 Prompt。"""
    return FOLLOW_UP_PROMPT.format(
        context=context,
        question=question,
        user_sql=user_sql,
        previous_feedback=previous_feedback,
        follow_up_question=follow_up_question,
    )


# ---------- 简单测试 ----------
if __name__ == "__main__":
    from nl2sql_loader import load_question_by_id, get_db_connection, TRAIN_DB

    print("=" * 60)
    print("任务2 测试：判题核心模块")
    print("=" * 60)

    qinfo = load_question_by_id(0)
    std_sql = qinfo["standard_sql"].replace("table_name", f"`{qinfo['table_schema']['name']}`")
    user_sql = std_sql  # 先用正确答案测试

    print(f"\n标准SQL: {std_sql}")
    ok, res, cols = safe_execute_sql(std_sql, TRAIN_DB)
    print(f"执行结果: ok={ok}, cols={cols}, rows={res[:3] if ok else res}")

    # 比对
    cmp = compare_results(res if ok else [], res if ok else [])
    print(f"比对结果: {cmp}")

    # 特征提取
    features = extract_sql_features(std_sql, qinfo["table_schema"])
    print(f"特征: {json.dumps(features, ensure_ascii=False)}")

    # 语义等价（自己和自己比）
    sem = semantic_equivalence_check(
        qinfo["question"], user_sql, features, qinfo["table_schema"]
    )
    print(f"语义等价: {sem}")

    # 反馈生成
    err_info = {"has_error": not ok, "error_msg": res if not ok else "", "table_schema": qinfo["table_schema"]}
    fb = generate_educational_feedback(qinfo["question"], user_sql, err_info, cmp)
    print(f"反馈: {json.dumps(fb, ensure_ascii=False, indent=2)}")
