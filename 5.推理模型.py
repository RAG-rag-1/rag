import requests
import chromadb

def ollama_embedding_by_api(text):
    """通过Ollama API获取文本的向量表示"""
    res = requests.post(
        url="http://127.0.0.1:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    embedding = res.json()['embedding']
    return embedding

def ollama_generate_by_api(prompt, model="deepseek-r1:1.5b", temperature=0.1):
    """通过Ollama API生成文本回复"""
    response = requests.post(
        url="http://127.0.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        }
    )
    return response.json()['response']

def query_knowledge_base(query_text, n_results=3):
    """查询知识库获取相关信息"""
    try:
        # 连接到Chroma数据库
        client = chromadb.PersistentClient(path="db/chroma_demo")
        collection = client.get_collection(name="all_knowledge_collection")
        
        # 获取查询向量
        query_embedding = ollama_embedding_by_api(query_text)
        
        # 执行查询
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return results['documents'][0], results['metadatas'][0]
    except Exception as e:
        print(f"查询知识库失败: {e}")
        return [], []

def generate_response(query_text, use_knowledge=True):
    """生成回复，可选是否使用知识库"""
    print(f"\n查询: {query_text}")
    
    if use_knowledge:
        # 从知识库获取相关信息
        relevant_docs, metadatas = query_knowledge_base(query_text)
        
        if relevant_docs:
            # 构建上下文
            context = "\n".join(relevant_docs)
            sources_info = "\n".join([f"来源: {m['filename']}, 片段 {m['chunk_index']+1}" for m in metadatas])
            
            # 构建带上下文的提示词
            prompt = f"""你是一个专业的助手，根据提供的参考信息回答用户问题。
参考信息:\n{context}\n
请基于以上参考信息，用中文回答用户问题: {query_text}\n"""
            
            print("\n已从知识库获取相关信息:")
            print(sources_info)
        else:
            # 没有找到相关信息，直接回答
            prompt = f"""请用中文回答用户问题: {query_text}\n"""
            print("\n知识库中未找到相关信息，将直接回答")
    else:
        # 不使用知识库，直接回答
        prompt = f"""请用中文回答用户问题: {query_text}\n"""
    
    # 生成回复
    try:
        response = ollama_generate_by_api(prompt)
        print(f"\n回复:")
        print(response)
        return response
    except Exception as e:
        print(f"生成回复失败: {e}")
        return "抱歉，我暂时无法回答这个问题。"

if __name__ == "__main__":
    # 测试不同类型的查询
    test_queries = [
        "什么是风寒感冒？",
        "入学需要准备哪些材料？",
        "学校有哪些专业？",
        "请解释一下脾胃虚寒的症状"
    ]
    
    print("=== 推理模型演示 ===")
    for query in test_queries:
        generate_response(query, use_knowledge=True)
        print("\n" + "-" * 80)