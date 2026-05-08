"""
app.py
Text-to-SQL 判题练习系统入口。
判题练习功能，Gradio 界面直接定义在此文件中。
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import gradio as gr

from agent_pipeline import run_judge, run_sql_grading
from nl2sql_loader import (
    load_question_by_id,
    get_random_question_indices,
    load_questions_by_indices,
    TRAIN_DB,
)
from judge_core import safe_execute_sql, build_follow_up_prompt

# ---------- 状态 ----------
_state = {
    "random_indices": [],
    "questions": {},
    "current_qid": None,
    "current_user_sql": "",
    "previous_feedback": "",
}


def _refresh_questions():
    """重新随机抽取 5 题，返回下拉框选项并自动加载第一题。"""
    indices = get_random_question_indices(count=5)
    questions = load_questions_by_indices(indices)
    _state["random_indices"] = indices
    _state["questions"] = questions
    choices = [(f"题目 {i+1}（原编号 #{idx+1}）", i) for i, idx in enumerate(indices)]
    # 自动加载第一题
    q_md, schema_md, std_sql, ans_md = _load_question(0)
    return gr.update(choices=choices, value=0), q_md, schema_md, std_sql, ans_md


def _load_question(option_index: int):
    """加载指定选项对应的题目信息。"""
    real_indices = _state["random_indices"]
    if option_index is None or option_index < 0 or option_index >= len(real_indices):
        return "请先点击「随机抽 5 题」", "", ""

    real_idx = real_indices[option_index]
    qinfo = _state["questions"].get(real_idx)
    if qinfo is None:
        qinfo = load_question_by_id(real_idx)

    _state["current_qid"] = real_idx

    question_md = f"**题目 {option_index + 1}（原编号 #{real_idx + 1}）**\n\n{qinfo['question']}"

    schema = qinfo["table_schema"]
    schema_md = f"### 表名：`{schema['name']}`\n\n"
    schema_md += "| 列编号 | 列名（中文） | 数据库列 | 类型 |\n"
    schema_md += "|--------|-------------|----------|------|\n"
    for i, (col, typ) in enumerate(zip(schema["columns"], schema.get("types", []))):
        schema_md += f"| {i+1} | {col} | `col_{i+1}` | {typ} |\n"

    std_sql = qinfo["standard_sql"].replace("table_name", f"`{schema['name']}`")

    # 标准答案 SQL 及执行结果
    answer_md = f"**标准 SQL：**\n```sql\n{std_sql}\n```\n\n"
    ok_std, std_rows, std_cols = safe_execute_sql(std_sql, TRAIN_DB, timeout=5)
    if ok_std:
        answer_md += "**执行结果：**\n\n"
        answer_md += "| " + " | ".join(std_cols) + " |\n"
        answer_md += "| " + " | ".join(["---"] * len(std_cols)) + " |\n"
        for row in std_rows:
            answer_md += "| " + " | ".join(str(c) for c in row) + " |\n"
    else:
        answer_md += f"❌ 标准 SQL 执行出错：{std_rows}"

    return question_md, schema_md, std_sql, answer_md


def _generate_sql(natural_language: str):
    """自然语言生成 SQL（与 LLM 交流），LLM 会读到当前随机抽的表结构。"""
    if not natural_language.strip():
        return "⚠️ 请输入自然语言描述", ""

    # 获取当前题目的表结构传给 LLM
    real_qid = _state.get("current_qid")
    qinfo = _state["questions"].get(real_qid) if real_qid is not None else None
    table_schema = qinfo.get("table_schema") if qinfo else None

    try:
        result = run_sql_grading(natural_language, table_schema=table_schema)
        sql = result.get("generated_sql", "").strip()
        return f"\n{sql}", sql
    except Exception as e:
        return f"❌ 生成失败：{e}", ""


def _run_sql(user_sql: str):
    """仅执行用户 SQL，返回 Markdown 表格。"""
    if not user_sql.strip():
        return "⚠️ 请输入 SQL 语句"
    _state["current_user_sql"] = user_sql
    ok, result, columns = safe_execute_sql(user_sql, TRAIN_DB, timeout=5)
    if not ok:
        return f"❌ **执行错误：** {result}"
    md = "| " + " | ".join(columns) + " |\n"
    md += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    for row in result:
        md += "| " + " | ".join(str(c) for c in row) + " |\n"
    return md


def _submit_judge(option_index: int, user_sql: str):
    """提交判题。"""
    if not user_sql.strip():
        return "⚠️ 请输入 SQL", "## 判题报告\n\n请输入 SQL 后提交判题。", ""

    real_indices = _state["random_indices"]
    if option_index is None or option_index < 0 or option_index >= len(real_indices):
        return "⚠️ 题目未加载", "", ""

    real_qid = real_indices[option_index]
    report = run_judge(real_qid, user_sql)
    _state["previous_feedback"] = report.get("feedback", "")

    # 执行结果（用户 SQL）
    exec_res = report.get("execution_result", {})
    if exec_res.get("success"):
        cols = exec_res.get("columns", [])
        rows = exec_res.get("rows", [])
        exec_md = "### 你的 SQL 执行结果\n\n"
        exec_md += "| " + " | ".join(cols) + " |\n"
        exec_md += "| " + " | ".join(["---"] * len(cols)) + " |\n"
        for row in rows:
            exec_md += "| " + " | ".join(str(c) for c in row) + " |\n"
    else:
        exec_md = f"❌ **执行失败：** {exec_res.get('error_msg', '未知错误')}"

    # 标准答案（独立展示）
    qinfo = _state["questions"].get(real_qid, {})
    answer_md = ""
    if qinfo:
        std_sql = qinfo["standard_sql"].replace("table_name", f"`{qinfo['table_schema']['name']}`")
        answer_md = f"**标准 SQL：**\n```sql\n{std_sql}\n```\n\n"
        ok_std, std_rows, std_cols = safe_execute_sql(std_sql, TRAIN_DB, timeout=5)
        if ok_std:
            answer_md += "**执行结果：**\n\n"
            answer_md += "| " + " | ".join(std_cols) + " |\n"
            answer_md += "| " + " | ".join(["---"] * len(std_cols)) + " |\n"
            for row in std_rows:
                answer_md += "| " + " | ".join(str(c) for c in row) + " |\n"
        else:
            answer_md += f"❌ 标准 SQL 执行出错：{std_rows}"

    # 判题报告
    status = report.get("status", "unknown")
    icon = {"correct": "✅", "partial": "⚠️", "incorrect": "❌"}.get(status, "📝")
    report_md = f"## {icon} 判题结果：{status.upper()}\n\n"
    report_md += f"**比对结果：** {report.get('comparison', {}).get('diff', '')}\n\n"
    report_md += f"**AI 语义判语：** {report.get('semantic_analysis', {}).get('reason', '')}\n\n"
    report_md += f"**修改建议：**\n\n{report.get('feedback', '')}\n\n"
    report_md += f"**推荐知识点：** `{report.get('knowledge_point', 'SQL 基础查询')}`"

    # 追问上下文
    qinfo = _state["questions"].get(real_qid, {})
    ctx_md = f"- **题目：** {qinfo.get('question', '')}\n"
    ctx_md += f"- **学生 SQL：** `{user_sql}`\n"
    ctx_md += f"- **反馈摘要：** {report.get('feedback', '')[:120]}..."

    return exec_md, report_md, ctx_md, answer_md


def _follow_up(follow_up_question: str):
    """追问。"""
    if not follow_up_question.strip():
        return "⚠️ 请输入追问内容"
    qinfo = _state["questions"].get(_state.get("current_qid"), {})
    user_sql = _state.get("current_user_sql", "")
    prev_fb = _state.get("previous_feedback", "")

    prompt = build_follow_up_prompt(
        context="（知识库上下文暂未接入）",
        question=qinfo.get("question", ""),
        user_sql=user_sql,
        previous_feedback=prev_fb,
        follow_up_question=follow_up_question,
    )
    try:
        from backend_utils import llm
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"❌ 追问回答出错：{e}"


def _reset():
    """重置。"""
    _state["current_qid"] = None
    _state["current_user_sql"] = ""
    _state["previous_feedback"] = ""
    return "", "", "", "", "", "", "", "", ""


# ---------- Gradio 界面 ----------
with gr.Blocks(title="SQL 判题练习系统") as demo:
    gr.Markdown("# 📝 SQL 判题练习系统")
    gr.Markdown("从真实 NL2SQL 数据集中随机抽取题目，编写 SQL 并获取引导式反馈。")

    with gr.Row():
        # 左侧面板
        with gr.Column(scale=1):
            gr.Markdown("### 🎲 题目抽取")
            refresh_btn = gr.Button("🔄 随机抽 5 题", variant="primary")
            qid_dropdown = gr.Dropdown(
                choices=[],
                value=None,
                label="选择题目",
            )
            load_q_btn = gr.Button("📖 加载题目", variant="secondary")

            gr.Markdown("---")
            gr.Markdown("### 📋 题目信息")
            question_display = gr.Markdown()
            schema_display = gr.Markdown()

            # 隐藏字段，存储标准 SQL
            hidden_std_sql = gr.Textbox(visible=False)

        # 右侧面板
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("✍️ 手写 SQL"):
                    sql_input = gr.Textbox(
                        label="请输入你的 SQL",
                        placeholder="SELECT col_1 FROM Table_xxx WHERE col_2 = '...'",
                        lines=8,
                    )
                with gr.TabItem("🤖 自然语言生成 SQL"):
                    nl_input = gr.Textbox(
                        label="用中文描述你想查什么（与 LLM 交流）",
                        placeholder="例如：查询票房占比大于10%的电影名称",
                        lines=3,
                    )
                    nl_gen_btn = gr.Button("✨ 生成 SQL", variant="secondary")
                    nl_output = gr.Textbox(label="生成的 SQL", lines=4)

            with gr.Row():
                run_btn = gr.Button("▶ 运行", variant="secondary")
                judge_btn = gr.Button("✅ 提交判题", variant="primary")
                reset_btn = gr.Button("🗑️ 重置", variant="stop")

    gr.Markdown("---")
    gr.Markdown("### 📊 结果区")
    with gr.Tabs():
        with gr.TabItem("执行结果"):
            exec_output = gr.Markdown()
        with gr.TabItem("标准答案"):
            answer_output = gr.Markdown()
        with gr.TabItem("判题报告"):
            report_output = gr.Markdown()
        with gr.TabItem("追问 AI"):
            follow_ctx = gr.Markdown(label="当前上下文")
            follow_input = gr.Textbox(
                label="追问内容",
                placeholder="例如：为什么这里要用 SUM 而不是 COUNT？",
                lines=2,
            )
            follow_btn = gr.Button("📤 发送", variant="primary")
            follow_output = gr.Textbox(label="AI 回答", lines=6)

    # 事件绑定
    refresh_btn.click(
        fn=_refresh_questions,
        inputs=[],
        outputs=[qid_dropdown, question_display, schema_display, hidden_std_sql, answer_output],
    )

    load_q_btn.click(
        fn=_load_question,
        inputs=[qid_dropdown],
        outputs=[question_display, schema_display, hidden_std_sql, answer_output],
    )

    nl_gen_btn.click(
        fn=_generate_sql,
        inputs=[nl_input],
        outputs=[nl_output, sql_input],
    )

    run_btn.click(
        fn=_run_sql,
        inputs=[sql_input],
        outputs=[exec_output],
    )

    judge_btn.click(
        fn=_submit_judge,
        inputs=[qid_dropdown, sql_input],
        outputs=[exec_output, report_output, follow_ctx, answer_output],
    )

    reset_btn.click(
        fn=_reset,
        inputs=[],
        outputs=[sql_input, nl_input, nl_output, exec_output, answer_output, report_output, follow_ctx, follow_input, follow_output, hidden_std_sql],
    )

    follow_btn.click(
        fn=_follow_up,
        inputs=[follow_input],
        outputs=[follow_output],
    )

if __name__ == "__main__":
    demo.launch()
