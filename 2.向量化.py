import requests
import os

def get_embedding(text):
    """获取单个文本的向量表示"""
    res = requests.post(
        url="http://127.0.0.1:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return res.json()['embedding']

def process_file(file_path):
    """处理单个文件，按空行切割"""
    with open(file_path, encoding='utf-8', mode='r') as fp:
        data = fp.read()
    
    # 根据换行切割
    chunk_list = data.split("\n\n")
    return [chunk for chunk in chunk_list if chunk]

def vectorize_all_files():
    """处理knowledge文件夹中的所有txt文件并进行向量化"""
    knowledge_dir = "knowledge"
    all_vectors = []
    all_texts = []
    
    # 遍历knowledge文件夹中的所有txt文件
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(knowledge_dir, filename)
            print(f"处理文件: {filename}")
            chunks = process_file(file_path)
            
            for chunk in chunks[:2]:  # 为了演示，只处理每个文件的前2个片段
                print(f"\n处理文本片段:\n{chunk[:100]}...")
                embedding = get_embedding(chunk)
                all_vectors.append(embedding)
                all_texts.append(chunk)
                print(f"向量维度: {len(embedding)}")
                print(f"向量前5个值: {embedding[:5]}")
    
    return all_texts, all_vectors

# 执行处理
if __name__ == "__main__":
    texts, vectors = vectorize_all_files()
    print(f"\n总共向量化了 {len(vectors)} 个文本片段")