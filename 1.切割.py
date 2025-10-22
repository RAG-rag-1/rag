import os

def process_file(file_path):
    """处理单个文件，按空行切割"""
    with open(file_path, encoding='utf-8', mode='r') as fp:
        data = fp.read()
    
    # 根据换行切割
    chunk_list = data.split("\n\n")
    chunk_list = [chunk for chunk in chunk_list if chunk]
    return chunk_list

def process_all_files():
    """处理knowledge文件夹中的所有txt文件"""
    knowledge_dir = "knowledge"
    all_chunks = []
    
    # 遍历knowledge文件夹中的所有txt文件
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(knowledge_dir, filename)
            print(f"处理文件: {filename}")
            chunks = process_file(file_path)
            all_chunks.extend(chunks)
            print(f"该文件切割成 {len(chunks)} 个片段")
    
    return all_chunks

# 执行处理
if __name__ == "__main__":
    all_chunks = process_all_files()
    print(f"\n总共处理了 {len(all_chunks)} 个片段")
    # 打印前3个片段作为示例
    print("\n前3个片段示例:")
    for i, chunk in enumerate(all_chunks[:3]):
        print(f"片段 {i+1}:\n{chunk}\n{'-'*50}")