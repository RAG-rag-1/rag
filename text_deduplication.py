import os
import re
import difflib
from datetime import datetime

def calculate_similarity(text1, text2):
    """计算两个文本的相似度，更准确地处理结构化内容"""
    # 预处理文本，移除标题标记，确保标题内容不影响相似度计算
    def preprocess(text):
        # 移除Markdown标题标记
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        # 移除其他格式标记
        text = re.sub(r'^===\s*|\s*===$', '', text, flags=re.MULTILINE)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # 对两段文本进行预处理
    processed_text1 = preprocess(text1)
    processed_text2 = preprocess(text2)
    
    # 使用SequenceMatcher计算相似度
    return difflib.SequenceMatcher(None, processed_text1, processed_text2).ratio()

def extract_content_from_file(file_path):
    """从文件中提取标题和正文内容，兼容多种格式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title_match = re.search(r'标题: (.*?)\n', content)
        title = title_match.group(1).strip() if title_match else "未知标题"
        
        # 提取正文内容
        content_match = re.search(r'=== 正文内容 ===\n\n(.*)', content, re.DOTALL)
        text = content_match.group(1) if content_match else content
        
        return title, text
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return None, None

def deduplicate_knowledge_base(knowledge_dir="knowledge", similarity_threshold=0.85):
    """去重知识库，保留最新版本的内容，增强对Markdown风格标题的支持"""
    if not os.path.exists(knowledge_dir):
        print(f"知识库目录不存在: {knowledge_dir}")
        return
    
    files = [f for f in os.listdir(knowledge_dir) if f.endswith('.txt')]
    if not files:
        print("知识库中没有找到txt文件")
        return
    
    print(f"开始处理 {len(files)} 个知识库文件...")
    
    # 用于存储文件信息和内容
    file_info = []
    for file in files:
        file_path = os.path.join(knowledge_dir, file)
        title, content = extract_content_from_file(file_path)
        if title and content:
            # 提取文件修改时间
            mtime = os.path.getmtime(file_path)
            # 计算内容哈希，用于快速比较完全相同的文件
            content_hash = hash(content)
            file_info.append({
                'file': file,
                'path': file_path,
                'title': title,
                'content': content,
                'mtime': mtime,
                'hash': content_hash
            })
    
    # 按标题对文件进行分组
    title_groups = {}
    for info in file_info:
        # 简化标题，用于分组
        simplified_title = re.sub(r'_\d{8}_\d{6}$', '', info['title'].split('_')[0])
        if simplified_title not in title_groups:
            title_groups[simplified_title] = []
        title_groups[simplified_title].append(info)
    
    # 对每个标题组进行去重
    files_to_remove = []
    for title, group in title_groups.items():
        if len(group) > 1:
            print(f"\n发现重复标题组: {title} ({len(group)}个文件)")
            # 按修改时间排序，保留最新的
            group.sort(key=lambda x: x['mtime'], reverse=True)
            
            # 比较第一个文件（最新的）与其他文件的相似度
            latest = group[0]
            print(f"  保留最新文件: {latest['file']} (修改时间: {datetime.fromtimestamp(latest['mtime']).strftime('%Y-%m-%d %H:%M:%S')})")
            
            for other in group[1:]:
                # 首先检查哈希值是否相同
                if latest['hash'] == other['hash']:
                    print(f"  完全重复文件: {other['file']} - 标记删除")
                    files_to_remove.append(other['path'])
                else:
                    # 计算相似度
                    similarity = calculate_similarity(latest['content'], other['content'])
                    if similarity >= similarity_threshold:
                        print(f"  高相似文件: {other['file']} (相似度: {similarity:.2f}) - 标记删除")
                        files_to_remove.append(other['path'])
                    else:
                        print(f"  低相似文件: {other['file']} (相似度: {similarity:.2f}) - 保留")
    
    # 执行删除操作
    if files_to_remove:
        print(f"\n准备删除 {len(files_to_remove)} 个重复文件")
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                print(f"  删除文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  删除文件失败 {os.path.basename(file_path)}: {e}")
    else:
        print("\n未发现需要删除的重复文件")
    
    print(f"\n去重完成！知识库中剩余 {len(files) - len(files_to_remove)} 个文件")

def main():
    """主函数"""
    knowledge_dir = "knowledge"
    # 可调整相似度阈值，值越高越严格，只删除非常相似的文件
    similarity_threshold = 0.85
    deduplicate_knowledge_base(knowledge_dir, similarity_threshold)

if __name__ == "__main__":
    main()
import shutil

def get_file_modification_time(file_path):
    """获取文件修改时间"""
    return os.path.getmtime(file_path)

def get_extraction_time(content):
    """从文件内容中提取提取时间"""
    time_pattern = r'提取时间: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    match = re.search(time_pattern, content)
    if match:
        time_str = match.group(1)
        try:
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S').timestamp()
        except:
            return None
    return None

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败 {file_path}: {e}")
        return None

def calculate_similarity(text1, text2):
    """计算两个文本的相似度"""
    # 提取正文内容进行比较
    content1 = re.search(r'=== 正文内容 ===(.+)', text1, re.DOTALL)
    content2 = re.search(r'=== 正文内容 ===(.+)', text2, re.DOTALL)
    
    if content1 and content2:
        text1 = content1.group(1).strip()
        text2 = content2.group(1).strip()
    
    # 使用difflib计算相似度
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def detect_duplicate_texts(folder_path, similarity_threshold=0.8):
    """检测相似文本"""
    files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    file_contents = {}
    file_times = {}
    
    # 读取所有文件内容和时间信息
    for file in files:
        file_path = os.path.join(folder_path, file)
        content = read_file_content(file_path)
        if content:
            file_contents[file] = content
            # 优先使用提取时间，如果没有则使用文件修改时间
            extract_time = get_extraction_time(content)
            if extract_time:
                file_times[file] = extract_time
            else:
                file_times[file] = get_file_modification_time(file_path)
    
    # 检测相似文件组
    duplicate_groups = []
    processed = set()
    
    for i, file1 in enumerate(files):
        if file1 in processed:
            continue
        group = [file1]
        processed.add(file1)
        
        for j, file2 in enumerate(files):
            if i != j and file2 not in processed:
                similarity = calculate_similarity(file_contents[file1], file_contents[file2])
                if similarity >= similarity_threshold:
                    group.append(file2)
                    processed.add(file2)
        
        if len(group) > 1:
            duplicate_groups.append(group)
    
    return duplicate_groups, file_times

def deduplicate_texts(folder_path, similarity_threshold=0.8):
    """自动去重，保留最新版本"""
    duplicate_groups, file_times = detect_duplicate_texts(folder_path, similarity_threshold)
    deleted_files = []
    
    for group in duplicate_groups:
        # 找出最新的文件
        latest_file = max(group, key=lambda x: file_times[x])
        print(f"\n检测到相似文本组:")
        print(f"  最新文件: {latest_file} ({datetime.fromtimestamp(file_times[latest_file])})")
        
        # 删除旧版本文件
        for file in group:
            if file != latest_file:
                file_path = os.path.join(folder_path, file)
                try:
                    os.remove(file_path)
                    deleted_files.append(file)
                    print(f"  删除旧文件: {file} ({datetime.fromtimestamp(file_times[file])})")
                except Exception as e:
                    print(f"  删除文件失败 {file}: {e}")
    
    return deleted_files

def main():
    knowledge_folder = "knowledge"
    knowledge_path = os.path.join(os.getcwd(), knowledge_folder)
    
    if not os.path.exists(knowledge_path):
        print(f"知识库文件夹不存在: {knowledge_path}")
        return
    
    print(f"开始检测知识库中的相似文本...")
    deleted_files = deduplicate_texts(knowledge_path)
    
    if deleted_files:
        print(f"\n去重完成！共删除 {len(deleted_files)} 个重复文件。")
    else:
        print("\n未检测到相似文本文件。")

if __name__ == "__main__":
    main()