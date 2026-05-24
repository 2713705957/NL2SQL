"""
backend_utils.py
后端共享工具函数与组件，供 frontend.py 与 app.py 使用，避免循环导入。
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import base64
import fitz  # PyMuPDF
import io
import requests
from PIL import Image

import gradio as gr
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from openai import OpenAI

# ---------- 嵌入与向量库 ----------
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="course_knowledge"
)

llm = ChatOpenAI(
    model="LongCat-Flash-Chat",              
    api_key="ak_2Ni8wX3x431J2lj0WX9lz3ME3No1x",
    base_url="https://api.longcat.chat/openai/v1",
    temperature=0.3
)

vision_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# ---------- RAG 链 ----------
prompt_template = """基于以下参考信息回答用户的问题。如果参考信息中没有相关内容，请如实说明。

参考信息：
{context}

用户问题：{question}

请用中文回答："""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)


def build_rag_chain(k=3):
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )
    return rag_chain, retriever


# ---------- 图像与 PDF 工具 ----------

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def answer_with_rag(question, num_docs):
    if not question.strip():
        return "请输入问题", ""
    rag_chain, retriever = build_rag_chain(k=int(num_docs))
    result = rag_chain.invoke(question)
    relevant_docs = retriever.invoke(question)
    sources = "\n\n".join([
        f"**来源 {i+1}:**\n{doc.page_content[:300]}"
        for i, doc in enumerate(relevant_docs)
    ])
    return result, sources


def answer_with_agent(question):
    from agent_pipeline import run_sql_grading
    if not question.strip():
        return "请输入问题", ""
    try:
        result = run_sql_grading(question)
        answer = f"""
**判题结果：** {result['final_grade']}

**生成的SQL：**
```sql
{result['generated_sql']}
```

**验证结果：** {result['validation_result']}

**执行结果：**
{result['execution_result']}

**详细反馈：**
""" + "\n".join([f"- {fb}" for fb in result['feedback']])
        sources = f"""
**Agent处理流程：**
1. 解析Agent：分析用户问题结构
2. SQL生成Agent：生成对应的SQL查询
3. 验证Agent：检查SQL语法正确性
4. 执行Agent：模拟SQL执行过程
5. 评分Agent：综合评估并给出分数

**最终得分：** {result['final_grade']}
        """
        return answer, sources
    except Exception as e:
        return f"Agent处理出错：{str(e)}", "请检查Agent配置和模型连接"


def answer_question(question, image_file, num_docs):
    if image_file is not None:
        try:
            image_base64 = encode_image(image_file)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question if question else "请描述这张图片。"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                        }
                    ]
                }
            ]
            response = vision_client.chat.completions.create(
                model="llama3.2-vision:11b",
                messages=messages,
                max_tokens=1024,
                stream=False
            )
            answer = response.choices[0].message.content
            sources = "**模式:** 视觉模型 (llama3.2-vision:11b)\n\n**说明:** 已根据上传的图片进行分析。"
            return answer, sources
        except Exception as e:
            return f"视觉模型处理出错：{str(e)}", "请检查Ollama服务是否启动及模型是否已拉取。"

    if not question.strip():
        return "请输入问题或上传图片", ""
    return answer_with_rag(question, num_docs)


def chat_with_image(image_path, question, model="llama3.2-vision:11b", timeout=30):
    try:
        image_base64 = encode_image(image_path)
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": question, "images": [image_base64]}],
            "stream": False,
            "options": {"num_predict": 512}
        }
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.Timeout:
        return "图像分析超时，跳过该图片分析。"
    except Exception as e:
        return f"图像分析出错: {str(e)}"


def extract_pdf_content(pdf_path, output_dir="pdf_extracted"):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted = {"pages": []}
    for page_num, page in enumerate(doc):
        page_data = {"page": page_num + 1, "text": page.get_text(), "images": []}
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = f"page{page_num+1}_img{img_idx+1}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            page_data["images"].append({
                "filename": image_filename,
                "path": image_path,
                "size": f"{len(image_bytes)/1024:.1f}KB"
            })
        extracted["pages"].append(page_data)
    doc.close()
    return extracted


def document_qa(pdf_content, question, model="llama3.2-vision:11b", max_images_to_analyze=5):
    all_text = ""
    image_analyses = []
    analyzed_image_count = 0
    for page in pdf_content["pages"]:
        all_text += f"\n--- 第{page['page']}页 ---\n{page['text']}"
        for img in page["images"]:
            if analyzed_image_count >= max_images_to_analyze:
                image_analyses.append({
                    "page": page["page"],
                    "filename": img["filename"],
                    "analysis": "[因图片数量较多，此图片未进行详细AI分析，仅保留引用]"
                })
                continue
            analysis = chat_with_image(
                img["path"],
                "简要描述这张图表的关键数据和结论。",
                model=model,
                timeout=20
            )
            image_analyses.append({
                "page": page["page"],
                "filename": img["filename"],
                "analysis": analysis
            })
            analyzed_image_count += 1

    context = f"文档文本内容：\n{all_text}\n\n"
    if image_analyses:
        context += "文档中图表的分析（部分可能因数量限制未详细分析）：\n"
        for ia in image_analyses:
            context += f"\n[第{ia['page']}页 {ia['filename']}]：{ia['analysis']}\n"

    prompt = f"""基于以下文档内容回答问题。文档包含文本和图表分析结果。

{context}

问题：{question}

请简洁明了地回答："""
    response = llm.invoke(prompt)
    return response.content


class DocumentProcessor:
    def __init__(self):
        self.pdf_content = None
        self.status = "未加载文档"

    def load_pdf(self, file):
        if file is None:
            return "请上传PDF文件"
        try:
            self.pdf_content = extract_pdf_content(file.name)
            total_pages = len(self.pdf_content["pages"])
            total_images = sum(len(p["images"]) for p in self.pdf_content["pages"])
            self.status = f"已加载：{total_pages}页，{total_images}张图片"
            return self.status
        except Exception as e:
            return f"解析失败: {str(e)}"

    def ask_question(self, question):
        if self.pdf_content is None:
            return "请先上传PDF文档"
        if not question.strip():
            return "请输入问题"
        try:
            return document_qa(self.pdf_content, question)
        except Exception as e:
            return f"问答出错: {str(e)}"

    def get_page_summary(self, page_num):
        if self.pdf_content is None:
            return "请先上传PDF文档"
        try:
            page_idx = int(page_num) - 1
            if page_idx < 0 or page_idx >= len(self.pdf_content["pages"]):
                return f"页码无效，文档共{len(self.pdf_content['pages'])}页"
            page = self.pdf_content["pages"][page_idx]
            summary = f"**第{page['page']}页**\n\n"
            summary += f"文本内容（前500字）：\n{page['text'][:500]}\n\n"
            summary += f"包含图片数量：{len(page['images'])}"
            return summary
        except Exception as e:
            return f"获取摘要出错: {str(e)}"
