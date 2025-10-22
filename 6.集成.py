import uuid
import chromadb
import requests
import os

def process_file(file_path):
    """处理单个文件，按空行切割"""
    with open(file_path, encoding='utf-8', mode='r') as fp:
        data = fp.read()
    
    # 根据换行切割
    chunk_list = data.split("\n\n")
    return [chunk for chunk in chunk_list if chunk]

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

def initialize_knowledge_base(collection_name="integrated_knowledge_collection"):
    """初始化知识库，处理knowledge文件夹中的所有文件"""
    print("=== 初始化知识库 ===")
    
    # 连接数据库
    client = chromadb.PersistentClient(path="db/chroma_demo")
    
    # 创建或重置集合
    print(f"创建/重置集合: {collection_name}")
    try:
        client.delete_collection(collection_name)
    except:
        pass  # 集合可能不存在，忽略错误
    
    collection = client.get_or_create_collection(name=collection_name)
    
    # 处理所有文件
    knowledge_dir = "knowledge"
    documents = []
    ids = []
    embeddings = []
    metadatas = []
    
    # 获取knowledge文件夹中的所有txt文件
    txt_files = [f for f in os.listdir(knowledge_dir) if f.endswith(".txt")]
    print(f"找到 {len(txt_files)} 个文本文件")
    
    total_chunks = 0
    # 处理每个文件
    for filename in txt_files:
        file_path = os.path.join(knowledge_dir, filename)
        print(f"\n处理文件: {filename}")
        
        # 切割文件
        chunks = process_file(file_path)
        print(f"该文件切割成 {len(chunks)} 个片段")
        total_chunks += len(chunks)
        
        # 处理每个片段
        for i, chunk in enumerate(chunks):
            try:
                # 生成唯一ID
                doc_id = str(uuid.uuid4())
                
                # 获取向量
                embedding = ollama_embedding_by_api(chunk)
                
                # 添加到列表
                documents.append(chunk)
                ids.append(doc_id)
                embeddings.append(embedding)
                metadatas.append({
                    "source": "knowledge_files",
                    "filename": filename,
                    "chunk_index": i
                })
                
                # 显示进度
                if (i + 1) % 5 == 0 or i + 1 == len(chunks):
                    print(f"  已处理 {i + 1}/{len(chunks)} 个片段")
                    
            except Exception as e:
                print(f"  处理片段 {i+1} 失败: {e}")
    
    # 批量插入到数据库
    if documents:
        print(f"\n准备插入 {len(documents)} 个文档到数据库...")
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        print(f"成功插入 {len(documents)} 个文档到数据库")
        print(f"总共处理了 {len(txt_files)} 个文件，{total_chunks} 个片段")
    else:
        print("没有找到文档需要插入")
    
    return collection

def retrieve_from_knowledge_base(query_text, collection, n_results=3):
    """从知识库中检索相关信息"""
    # 获取查询向量
    query_embedding = ollama_embedding_by_api(query_text)
    
    # 执行查询
    results = collection.query(
        query_embeddings=[query_embedding],
        query_texts=[query_text],
        n_results=n_results
    )
    
    return results

def generate_answer(query_text, collection):
    """根据查询生成回答"""
    print(f"\n=== 用户查询 ===")
    print(f"问题: {query_text}")
    
    # 从知识库检索相关信息
    results = retrieve_from_knowledge_base(query_text, collection)
    
    # 提取相关文档
    relevant_docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    
    if relevant_docs:
        # 构建上下文
        context = "\n".join(relevant_docs)
        
        # 显示检索到的信息
        print(f"\n=== 检索到的相关信息 ===")
        for i, (doc, dist, meta) in enumerate(zip(relevant_docs, distances, metadatas)):
            print(f"\n相关文档 {i+1} (相似度: {1-dist:.4f}):")
            print(f"来源: {meta['filename']}, 片段 {meta['chunk_index']+1}")
            print(f"内容预览: {doc[:150]}..." if len(doc) > 150 else f"内容: {doc}")
        
        # 构建提示词
        prompt = f"""你是一个专业的助手，任务是根据提供的参考信息回答用户问题。
请严格基于参考信息进行回答，如果参考信息不足以回答问题，请回复'根据现有信息无法回答该问题'，不要编造信息。

参考信息:\n{context}

用户问题: {query_text}

回答:
"""
    else:
        print("\n未检索到相关信息")
        prompt = f"""用户问题: {query_text}

回答:
"""
    
    # 生成回答
    try:
        print("\n=== 生成回答 ===")
        answer = ollama_generate_by_api(prompt)
        print(answer)
        return answer
    except Exception as e:
        error_msg = f"生成回答失败: {e}"
        print(error_msg)
        return error_msg

def main():
    """主函数"""
    # 初始化知识库
    collection = initialize_knowledge_base()
    
    # 演示查询
    demo_queries = [
        "请介绍一下风寒感冒的症状和治疗方法",
        "入学需要做哪些准备？",
        "学校有哪些专业？",
        "请解释一下脾胃虚寒的症状",
        "专业介绍中包含哪些内容？"
    ]
    
    print("\n=== 开始演示查询 ===")
    for query in demo_queries:
        generate_answer(query, collection)
        print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
