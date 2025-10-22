import chromadb
import uuid
import requests
import os

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

def process_file(file_path):
    """处理单个文件，按空行切割"""
    with open(file_path, encoding='utf-8', mode='r') as fp:
        data = fp.read()
    
    # 根据换行切割
    chunk_list = data.split("\n\n")
    return [chunk for chunk in chunk_list if chunk]

def load_all_files_to_db():
    """加载knowledge文件夹中的所有txt文件到Chroma数据库"""
    # 初始化数据库连接
    client = chromadb.PersistentClient(path="db/chroma_demo")
    
    # 创建或获取集合
    collection_name = "all_knowledge_collection"
    collection = client.get_or_create_collection(name=collection_name)
    
    # 清空集合，重新加载
    collection.delete(where={"source": "knowledge_files"})  # 删除之前的文档
    
    knowledge_dir = "knowledge"
    documents = []
    ids = []
    embeddings = []
    metadatas = []
    
    print(f"开始处理knowledge文件夹中的文件并加载到数据库...")
    
    # 遍历knowledge文件夹中的所有txt文件
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(knowledge_dir, filename)
            print(f"处理文件: {filename}")
            chunks = process_file(file_path)
            print(f"该文件切割成 {len(chunks)} 个片段")
            
            for i, chunk in enumerate(chunks):
                # 生成唯一ID
                doc_id = str(uuid.uuid4())
                
                try:
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
                    
                    print(f"处理片段 {i+1}/{len(chunks)}")
                    
                except Exception as e:
                    print(f"处理片段 {i+1} 失败: {e}")
    
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
    else:
        print("没有找到文档需要插入")
    
    return collection

def query_knowledge(query_text, collection):
    """查询知识库"""
    print(f"\n查询: {query_text}")
    # 获取查询向量
    query_embedding = ollama_embedding_by_api(query_text)
    
    # 执行查询
    results = collection.query(
        query_embeddings=[query_embedding],
        query_texts=[query_text],
        n_results=3
    )
    
    # 打印查询结果
    print(f"找到 {len(results['documents'][0])} 个相关结果:")
    for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
        print(f"\n结果 {i+1} (相似度: {1-dist:.4f}):")
        print(f"{doc[:200]}..." if len(doc) > 200 else doc)
        print(f"来源: {results['metadatas'][0][i]['filename']}, 片段 {results['metadatas'][0][i]['chunk_index']+1}")
    
    return results

if __name__ == "__main__":
    # 加载所有文件到数据库
    collection = load_all_files_to_db()
    
    # 执行示例查询
    example_queries = ["感冒", "入学", "专业"]
    for query in example_queries:
        query_knowledge(query, collection)