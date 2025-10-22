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

def process_all_files():
    """处理knowledge文件夹中的所有txt文件并进行向量化"""
    knowledge_dir = "knowledge"
    all_chunks_with_vectors = []
    
    # 遍历knowledge文件夹中的所有txt文件
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(knowledge_dir, filename)
            print(f"\n处理文件: {filename}")
            chunks = process_file(file_path)
            print(f"该文件切割成 {len(chunks)} 个片段")
            
            for i, chunk in enumerate(chunks):
                # 为了演示，限制每个文件处理的片段数量
                if i >= 2:  # 每个文件只处理前2个片段
                    break
                
                print(f"\n处理片段 {i+1}:")
                print(f"文本内容: {chunk[:80]}...")
                try:
                    vector = ollama_embedding_by_api(chunk)
                    all_chunks_with_vectors.append({
                        "filename": filename,
                        "chunk_index": i,
                        "text": chunk,
                        "vector": vector
                    })
                    print(f"向量维度: {len(vector)}")
                except Exception as e:
                    print(f"向量化失败: {e}")
    
    return all_chunks_with_vectors

def run():
    """运行主函数"""
    results = process_all_files()
    print(f"\n总共处理了 {len(results)} 个文本片段并向量化")

if __name__ == '__main__':
    run()