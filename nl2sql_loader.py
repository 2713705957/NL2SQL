"""
nl2sql_loader.py
数据集加载模块：读取 NL2SQL 数据集，提供题目、表结构、标准 SQL 的加载与转换。
"""

import json
import random
import sqlite3
from typing import Any

# 数据集路径（相对于项目根目录）
DATA_DIR = "./nl2sql-TableQA-ch/nl2sql-TableQA-ch/train"
TRAIN_JSON = f"{DATA_DIR}/train.json"
TRAIN_TABLES_JSON = f"{DATA_DIR}/train.tables.json"
TRAIN_DB = f"{DATA_DIR}/train.db"

# 映射规则
AGG_MAP = {
    0: "",      # 无聚合
    1: "AVG",
    2: "MAX",
    3: "MIN",
    4: "COUNT",
    5: "SUM",
}

OP_MAP = {
    0: ">",
    1: "<",
    2: "=",
    3: "!=",
}

COND_CONN_MAP = {
    0: "",      # 单个条件，无连接符
    1: "AND",
    2: "OR",
}


def load_tables(limit: int = 100) -> dict[str, dict[str, Any]]:
    """
    读取 train.tables.json，返回 {table_id: {name, columns, types, title}} 映射。
    为控制内存，默认只读取前 100 个表（足够覆盖前 5 题）。
    """
    tables = {}
    count = 0
    with open(TRAIN_TABLES_JSON, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            table_id = item["id"]
            tables[table_id] = {
                "name": item["name"],
                "columns": item["header"],
                "types": item.get("types", []),
                "title": item.get("title", ""),
            }
            count += 1
            if count >= limit:
                break
    return tables


def load_table_by_id(table_id: str) -> dict[str, Any] | None:
    """
    按需从 train.tables.json 中查找指定 table_id 的表结构。
    """
    with open(TRAIN_TABLES_JSON, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item["id"] == table_id:
                return {
                    "name": item["name"],
                    "columns": item["header"],
                    "types": item.get("types", []),
                    "title": item.get("title", ""),
                }
    return None


# 全局缓存，避免重复读取
_TABLES_CACHE: dict[str, dict[str, Any]] | None = None
_QUESTIONS_CACHE: list[dict[str, Any]] | None = None


def _load_questions_raw(limit: int = 5) -> list[dict[str, Any]]:
    """内部函数：流式读取 train.json 前 limit 条。"""
    questions = []
    with open(TRAIN_JSON, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            questions.append(json.loads(line))
            if len(questions) >= limit:
                break
    return questions


def get_tables() -> dict[str, dict[str, Any]]:
    """获取表结构映射（带缓存）。"""
    global _TABLES_CACHE
    if _TABLES_CACHE is None:
        _TABLES_CACHE = load_tables()
    return _TABLES_CACHE


def get_table_schema(table_id: str) -> dict[str, Any]:
    """获取指定 table_id 的表结构，优先走缓存，未命中则按需加载。"""
    tables = get_tables()
    if table_id in tables:
        return tables[table_id]
    schema = load_table_by_id(table_id)
    if schema is not None:
        tables[table_id] = schema  # 回填缓存
        return schema
    return {"name": f"Table_{table_id}", "columns": [], "types": [], "title": ""}


def get_questions(limit: int = 5) -> list[dict[str, Any]]:
    """获取题目列表（带缓存，若缓存不足则重新加载）。"""
    global _QUESTIONS_CACHE
    if _QUESTIONS_CACHE is None or len(_QUESTIONS_CACHE) < limit:
        _QUESTIONS_CACHE = _load_questions_raw(limit=limit)
    return _QUESTIONS_CACHE


def count_total_questions() -> int:
    """统计 train.json 总行数。"""
    count = 0
    with open(TRAIN_JSON, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


def get_random_question_indices(count: int = 5) -> list[int]:
    """
    从数据集中随机抽取 count 个不重复的题号（0-based 索引）。
    返回排序后的索引列表，便于顺序展示。
    """
    total = count_total_questions()
    if count >= total:
        return list(range(total))
    indices = sorted(random.sample(range(total), count))
    return indices


def load_questions_by_indices(indices: list[int]) -> dict[int, dict[str, Any]]:
    """
    根据索引列表流式读取 train.json，返回 {index: question_info}。
    要求 indices 已排序。
    """
    result: dict[int, dict[str, Any]] = {}
    target_set = set(indices)
    current_idx = 0
    with open(TRAIN_JSON, "r", encoding="utf-8") as f:
        for line in f:
            if current_idx in target_set:
                item = json.loads(line.strip())
                table_id = item["table_id"]
                table_schema = get_table_schema(table_id)
                sql_dict = item["sql"]
                standard_sql = dict_to_sql(sql_dict)
                result[current_idx] = {
                    "question_id": current_idx,
                    "question": item["question"],
                    "sql_dict": sql_dict,
                    "table_id": table_id,
                    "table_schema": table_schema,
                    "standard_sql": standard_sql,
                }
                if len(result) == len(target_set):
                    break
            current_idx += 1
    return result


def load_question_by_id(qid: int) -> dict[str, Any]:
    """
    根据题目编号（从 0 开始）加载题目信息。
    返回字典包含：question, sql_dict, table_id, table_schema, standard_sql。
    """
    questions = get_questions(limit=max(qid + 1, 5))
    if qid < 0 or qid >= len(questions):
        raise IndexError(f"题目编号 {qid} 超出范围，当前仅加载了 {len(questions)} 条数据")

    item = questions[qid]
    table_id = item["table_id"]
    table_schema = get_table_schema(table_id)

    sql_dict = item["sql"]
    standard_sql = dict_to_sql(sql_dict, table_schema["columns"])

    return {
        "question_id": qid,
        "question": item["question"],
        "sql_dict": sql_dict,
        "table_id": table_id,
        "table_schema": table_schema,
        "standard_sql": standard_sql,
    }


def dict_to_sql(sql_dict: dict[str, Any], _table_cols: list[str] | None = None) -> str:
    """
    将 sql 字典转换为标准 SQL 字符串。
    注意：数据库中实际列名为 col_1, col_2...，因此 _table_cols 仅作兼容保留。

    规则：
    - agg 映射 0-5：0 空, 1 AVG, 2 MAX, 3 MIN, 4 COUNT, 5 SUM
    - op 映射 0-3：0 >, 1 <, 2 =, 3 !=
    - 字符串值加引号
    - 多条件用 AND/OR 连接（由 cond_conn_op 决定）
    """
    # 数据库中实际列名为 col_1, col_2, ...
    # header 仅用于展示，不参与 SQL 生成
    table_name = "table_name"  # 占位，实际执行时会替换为真实表名

    def _get_db_col_name(col_idx: int) -> str:
        return f"col_{col_idx + 1}"

    # SELECT 部分
    sel_list = sql_dict.get("sel", [])
    agg_list = sql_dict.get("agg", [])

    select_parts = []
    for i, col_idx in enumerate(sel_list):
        col_name = _get_db_col_name(col_idx)
        agg = agg_list[i] if i < len(agg_list) else 0
        agg_func = AGG_MAP.get(agg, "")
        if agg_func:
            select_parts.append(f"{agg_func}({col_name})")
        else:
            select_parts.append(col_name)

    select_clause = ", ".join(select_parts) if select_parts else "*"

    # WHERE 部分
    conds = sql_dict.get("conds", [])
    cond_conn_op = sql_dict.get("cond_conn_op", 0)
    conn_op = COND_CONN_MAP.get(cond_conn_op, "AND") or "AND"

    where_parts = []
    for cond in conds:
        if len(cond) != 3:
            continue
        col_idx, op, val = cond
        col_name = _get_db_col_name(col_idx)
        operator = OP_MAP.get(op, "=")
        # 字符串加引号，数字保持原样
        if isinstance(val, str):
            val_str = f"'{val}'"
        else:
            val_str = str(val)
        where_parts.append(f"{col_name} {operator} {val_str}")

    where_clause = f" WHERE {f' {conn_op} '.join(where_parts)}" if where_parts else ""

    sql = f"SELECT {select_clause} FROM {table_name}{where_clause}"
    return sql


def get_standard_answer(qid: int) -> str:
    """返回可直接执行的标准 SQL（已替换真实表名）。"""
    qinfo = load_question_by_id(qid)
    sql = qinfo["standard_sql"]
    table_name = qinfo["table_schema"]["name"]
    return sql.replace("table_name", f"`{table_name}`")


def get_db_connection() -> sqlite3.Connection:
    """获取训练数据库连接。"""
    return sqlite3.connect(TRAIN_DB)


def get_table_preview(table_name: str, limit: int = 5) -> tuple[list[str], list[list[Any]]]:
    """
    获取指定表的前 limit 行数据，用于展示表结构示例。
    返回 (columns, rows)。
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {limit}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    finally:
        conn.close()


# 测试入口
if __name__ == "__main__":
    print("=" * 60)
    print("任务1 测试：加载前 5 条数据")
    print("=" * 60)

    for i in range(5):
        info = load_question_by_id(i)
        print(f"\n题目 {i + 1}:")
        print(f"  问题: {info['question']}")
        print(f"  表ID: {info['table_id']}")
        print(f"  表名: {info['table_schema']['name']}")
        print(f"  列名: {info['table_schema']['columns']}")
        print(f"  SQL字典: {json.dumps(info['sql_dict'], ensure_ascii=False)}")
        print(f"  标准SQL: {info['standard_sql']}")
        print(f"  可执行SQL: {get_standard_answer(i)}")

        # 尝试执行标准 SQL 查看结果
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(get_standard_answer(i))
            result = cursor.fetchall()
            print(f"  执行结果（前3行）: {result[:3]}")
            conn.close()
        except Exception as e:
            print(f"  执行出错: {e}")
