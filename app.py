import os
import re
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 知识库存储
knowledge_base = {}
knowledge_initialized = False

# 读取知识库文件
def load_knowledge_file(file_path):
    """从文件中加载知识库内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取知识库文件失败 {file_path}: {str(e)}")
        return ""

# 初始化知识库
def initialize_knowledge():
    """初始化所有知识库文件"""
    global knowledge_base, knowledge_initialized
    knowledge_base = {}
    
    # 知识库文件夹路径
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'knowledge')
    
    # 检查知识库文件夹是否存在
    if not os.path.exists(knowledge_dir):
        print(f"知识库文件夹不存在: {knowledge_dir}")
        return False
    
    # 读取所有txt文件
    for filename in os.listdir(knowledge_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(knowledge_dir, filename)
            content = load_knowledge_file(file_path)
            if content:
                # 使用文件名作为知识库标题
                title = os.path.splitext(filename)[0]
                knowledge_base[title] = {
                    'file': filename,
                    'content': content
                }
                print(f"成功加载知识库: {title}")
    
    knowledge_initialized = len(knowledge_base) > 0
    return knowledge_initialized



# 关键词匹配函数
def find_relevant_content(query, knowledge_content, file_name):
    """在知识库内容中查找与查询相关的部分，特别关注各级标题"""
    # 转换为小写用于匹配
    query_lower = query.lower()
    
    # 分词并计算关键词，过滤停用词
    stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    query_words = [word for word in query_lower.split() if len(word) > 1 and word not in stop_words]
    
    # 特殊关键词匹配，提高对毕业条件等重要信息的识别
    special_keywords = {'毕业', '条件', '学位', '学分', '修业', '年限'}
    has_special_keyword = len(set(query_words) & special_keywords) > 0
    
    relevant_sections = []
    
    # 特殊处理answers.txt格式的问答对
    if "answers.txt" in file_name:
        # 按行分割内容
        lines = knowledge_content.strip().split('\n')
        
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('答：'):
                # 检查是否是问题行（格式如：数字. 问题？）
                question_match = re.search(r'\d+\.\s*(.+?)[？?]', line)
                if question_match:
                    question_text = question_match.group(1).lower()
                    section_score = 0
                    matched_words = set()
                    
                    # 计算问题与查询的相关性得分
                    # 1. 完全匹配
                    if query_lower in question_text or question_text in query_lower:
                        section_score += 20  # 提高精确匹配权重
                    
                    # 2. 关键词匹配 - 使用过滤后的关键词
                    if query_words:
                        question_words = [word for word in question_text.split() if len(word) > 1]
                        # 计算共同关键词数量
                        common_words = set(query_words) & set(question_words)
                        matched_words.update(common_words)
                        section_score += len(common_words) * 5
                        
                        # 计算关键词覆盖率
                        coverage_ratio = len(common_words) / len(query_words)
                        if coverage_ratio >= 0.8:
                            section_score += 12  # 提高高覆盖率的权重
                        elif coverage_ratio >= 0.6:
                            section_score += 6
                        elif coverage_ratio >= 0.5:
                            section_score += 3
                    
                    # 3. 检查核心概念匹配
                    for keyword in ['建议', '如何', '什么', '为什么', '怎样', '是否', '多久', '哪里']:
                        if keyword in query_lower and keyword in question_text:
                            section_score += 4
                    
                    # 如果匹配了所有查询词，给予额外权重
                    if query_words and len(matched_words) == len(query_words):
                        section_score *= 1.5
                    
                    # 4. 如果有答案行，将问题和答案组合
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('答：'):
                        full_content = line + '\n' + lines[i + 1].strip()
                    else:
                        full_content = line
                    
                    # 提高阈值以增加精确性
                    if section_score >= 12:
                        relevant_sections.append((section_score, full_content))
    else:
        # 常规文本处理 - 按行分割以更好地捕获结构化信息
        lines = knowledge_content.strip().split('\n')
        
        # 标题识别模式，支持多级标题（增加对Markdown风格标题的支持）
        title_patterns = [
            (r'^#\s+(.+)', 1),          # Markdown一级标题（如# 标题）
            (r'^##\s+(.+)', 2),         # Markdown二级标题（如## 标题）
            (r'^###\s+(.+)', 3),        # Markdown三级标题（如### 标题）
            (r'^####\s+(.+)', 4),       # Markdown四级标题（如#### 标题）
            (r'^#####\s+(.+)', 5),      # Markdown五级标题（如##### 标题）
            (r'^######\s+(.+)', 6),     # Markdown六级标题（如###### 标题）
            (r'^===\s*(.+?)\s*===', 0),  # 一级标题（如=== 正文内容 ===）
            (r'^(\d+)\s+(.+)', 1),      # 一级标题（如1 标题）
            (r'^第[一二三四五六七八九十百]+章\s+(.+)', 1),  # 一级标题（如第一章 标题）
            (r'^[一二三四五六七八九十百]+\s+(.+)', 1),    # 一级标题（如一 标题）
            (r'^(\d+)\.(.+)', 2),      # 二级标题（如1.1 标题）
            (r'^[（(]\d+[）)]\s*[\u4e00-\u9fa5]+', 2),  # 二级标题（如（一）标题）
            (r'^(\d+)\.(\d+)\.(.+)', 3),  # 三级标题（如1.1.1 标题）
            (r'^(\d+)\.(\d+)\.(\d+)\.(.+)', 4)  # 四级标题（如1.1.1.1 标题）
        ]
        
        # 存储标题行号和层级
        title_positions = []
        for i, line in enumerate(lines):
            line = line.strip()
            for pattern, level in title_patterns:
                if re.match(pattern, line):
                    title_positions.append((i, level, line))
                    break
        
        # 将连续的相关行合并为段落，并特别关注标题
        current_section = []
        current_score = 0
        current_matched_words = set()
        
        # 记录当前段落之前的所有标题，以便在匹配时包含相关标题
        recent_titles = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # 如果是空行，处理当前段落并重置
                if current_section:
                    full_section = ' '.join(current_section)
                    relevant_sections.append((current_score, full_section))
                    current_section = []
                    current_score = 0
                    current_matched_words = set()
                continue
            
            # 检查是否是标题行
            is_title = False
            for _, _, title_line in title_positions:
                if line == title_line:
                    is_title = True
                    # 将当前标题添加到recent_titles
                    recent_titles.append(line)
                    # 限制recent_titles数量，只保留最近的几个标题
                    if len(recent_titles) > 3:
                        recent_titles.pop(0)
                    break
            
            # 计算当前行的得分
            line_lower = line.lower()
            line_score = 0
            line_matched_words = set()
            
            # 1. 增强的标题匹配 - 支持所有级别标题
            for pattern, level in title_patterns:
                if re.match(pattern, line):
                    # 标题匹配关键词
                    if any(keyword in line_lower for keyword in query_words):
                        line_score += 40 - level * 5  # 层级越低权重越高
                    # 标题包含完整查询
                    if query_lower in line_lower:
                        line_score += 30
                    break
            
            # 2. 检查整行匹配
            if query_lower in line_lower:
                line_score += 15
            
            # 3. 针对毕业条件等特殊查询的增强匹配
            if has_special_keyword and any(keyword in line_lower for keyword in special_keywords):
                line_score += 10  # 对毕业条件相关内容增加额外权重
            
            # 4. 使用过滤后的关键词进行匹配
            if query_words:
                line_words = line_lower.split()
                # 计算共同关键词数量
                common_words = set(query_words) & set(line_words)
                line_matched_words.update(common_words)
                line_score += len(common_words) * 4
                
                # 计算关键词覆盖率
                coverage_ratio = len(common_words) / len(query_words)
                if coverage_ratio >= 0.8:
                    line_score += 10
                elif coverage_ratio >= 0.6:
                    line_score += 5
                elif coverage_ratio >= 0.5:
                    line_score += 2
            
            # 5. 特殊处理包含顿号的列表行（通常是课程列表）
            if '、' in line and any(keyword in line_lower for keyword in query_words):
                line_score += 10  # 提高课程列表的权重
            
            # 6. 如果匹配了所有查询词，给予额外权重
            if query_words and len(line_matched_words) == len(query_words):
                line_score *= 1.5
            
            # 决定是否将此行添加到当前段落
            # 降低阈值以捕获更多可能相关的内容，特别是标题
            threshold = 8 if has_special_keyword else 9
            if line_score >= threshold:  # 根据是否包含特殊关键词调整阈值
                # 如果当前段开始，并且有recent_titles，将最近的标题添加到段落开头
                if not current_section and recent_titles:
                    # 添加最近的标题，保持层级关系
                    current_section.extend(recent_titles)
                current_section.append(line)
                current_score = max(current_score, line_score)  # 以段落中最高分为段落分
                current_matched_words.update(line_matched_words)
            elif current_section and is_title:  # 即使不相关，但如果是标题也保留
                current_section.append(line)
                recent_titles.append(line)
                # 限制recent_titles数量
                if len(recent_titles) > 3:
                    recent_titles.pop(0)
            elif current_section:  # 如果当前有段落在构建，但这行不太相关，可能是段落结束
                full_section = ' '.join(current_section)
                # 段落最终得分检查
                final_threshold = 11 if has_special_keyword else 13
                if current_score >= final_threshold:
                    relevant_sections.append((current_score, full_section))
                current_section = []
                current_score = 0
                current_matched_words = set()
        
        # 处理最后一个段落
        final_threshold = 11 if has_special_keyword else 13
        if current_section and current_score >= final_threshold:
            full_section = ' '.join(current_section)
            relevant_sections.append((current_score, full_section))
        
        # 如果没有找到相关内容，尝试专门查找标题
        if not relevant_sections:
            # 专门查找与查询相关的标题
            for i, level, title_line in title_positions:
                title_lower = title_line.lower()
                title_score = 0
                
                # 检查标题中是否包含查询关键词
                if any(keyword in title_lower for keyword in query_words):
                    title_score += 20 - level * 3
                
                # 检查标题是否包含完整查询
                if query_lower in title_lower:
                    title_score += 30
                
                # 如果标题相关，收集标题及其可能的内容
                if title_score >= 15:
                    title_content = [title_line]
                    # 收集标题后的几行内容
                    for j in range(i + 1, min(i + 8, len(lines))):  # 增加收集行数
                        next_line = lines[j].strip()
                        # 检查是否是下一个标题
                        is_next_title = False
                        for pattern, _ in title_patterns:
                            if re.match(pattern, next_line):
                                is_next_title = True
                                break
                        if not is_next_title and next_line:
                            title_content.append(next_line)
                        else:
                            break
                    relevant_sections.append((title_score, ' '.join(title_content)))
        
        # 如果仍然没有找到，尝试更宽松的匹配
        if not relevant_sections:
            # 尝试按句子匹配，更精确地找到相关内容
            sentences = re.split(r'[。！？.!?]', knowledge_content)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_lower = sentence.lower()
                sentence_score = 0
                
                # 检查关键词匹配
                if query_words:
                    sentence_words = sentence_lower.split()
                    common_words = set(query_words) & set(sentence_words)
                    sentence_score += len(common_words) * 5
                
                # 检查整句匹配
                if query_lower in sentence_lower:
                    sentence_score += 15
                
                # 检查包含顿号的列表
                if '、' in sentence and any(keyword in sentence_lower for keyword in query_words):
                    sentence_score += 10
                
                # 对特殊关键词查询降低阈值
                match_threshold = 9 if has_special_keyword else 11
                if sentence_score >= match_threshold:
                    relevant_sections.append((sentence_score, sentence))
    
    # 按得分排序
    relevant_sections.sort(reverse=True, key=lambda x: x[0])
    
    # 返回前5个最相关的结果，增加找到毕业条件等重要信息的概率
    return [section for score, section in relevant_sections[:5]]

# 简化段落内容

def simplify_text(text):
    """简化文本内容，提取关键信息，移除无关元数据"""
    # 移除元数据信息（如发布日期、点击量等）
    text = re.sub(r'发布日期[:：]\s*\d{4}-\d{2}-\d{2}', '', text)
    text = re.sub(r'点击量[:：]\s*\d+', '', text)
    
    # 移除多余的空行和空格，但保留合理的空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 完全移除长度限制，确保所有内容都能显示
    return text

# 查询处理函数
def process_query(query):
    """处理用户查询并返回回答"""
    global knowledge_initialized
    
    query = query.strip()
    print(f"处理查询: '{query}'")
    
    # 检查是否询问系统相关信息
    if any(word in query.lower() for word in ["系统", "功能", "介绍", "说明", "帮助"]):
        return "这是一个基于知识库的问答系统，目前包含多个知识库文件，您可以提问相关内容。"
    
    # 检查知识库是否初始化
    if not knowledge_initialized:
        return "知识库尚未初始化，请先点击页面上的'初始化知识库'按钮。"
    
    # 特殊关键词识别，提高对毕业条件等重要信息的处理
    special_keywords = {'毕业', '条件', '学位', '学分', '修业', '年限'}
    has_special_keyword = any(keyword in query.lower() for keyword in special_keywords)
    
    # 在所有知识库中查找相关内容
    all_relevant = []
    
    for title, knowledge in knowledge_base.items():
        # 传递文件名给匹配函数
        relevant = find_relevant_content(query, knowledge['content'], knowledge['file'])
        if relevant:
            # 根据查询类型采用不同的内容合并策略
            if has_special_keyword:
                # 对于毕业条件等特殊查询，合并所有找到的相关段落
                # 按相关性顺序合并，确保重要信息优先显示
                merged_content = ' '.join(relevant[:3])  # 合并前3个最相关的内容
            else:
                # 对于普通查询，优先保留包含课程列表的内容
                course_sections = [section for section in relevant if '、' in section]
                other_sections = [section for section in relevant if '、' not in section]
                
                # 先合并课程列表部分，再添加其他相关内容
                merged_content = ' '.join(course_sections + other_sections[:1])
            
            all_relevant.append((title, merged_content, knowledge['file']))
    
    # 按相关性排序（这里简化处理，假设第一个是最相关的）
    if all_relevant:
        # 只使用最相关的信息来构建回答
        title, best_section, file_name = all_relevant[0]
        
        # 简化内容，移除元数据但保留所有实际内容
        simplified_content = simplify_text(best_section)
        
        # 构建回答，确保来源格式清晰
        # 移除文件名中的.txt后缀
        simple_file_name = file_name.replace('.txt', '')
        return f"{simplified_content} [来源: {simple_file_name}]"
    else:
        # 未找到相关内容，但对于特殊关键词查询，尝试更宽松的搜索
        if has_special_keyword:
            # 尝试在所有知识库中进行更宽松的搜索
            for title, knowledge in knowledge_base.items():
                content_lower = knowledge['content'].lower()
                # 检查是否包含任何特殊关键词
                if any(keyword in content_lower for keyword in special_keywords):
                    # 提取包含特殊关键词的行
                    relevant_lines = []
                    for line in knowledge['content'].split('\n'):
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in special_keywords):
                            relevant_lines.append(line.strip())
                    
                    if relevant_lines:
                        # 合并找到的行并返回
                        merged_content = ' '.join(relevant_lines[:5])  # 限制返回行数
                        simplified_content = simplify_text(merged_content)
                        simple_file_name = knowledge['file'].replace('.txt', '')
                        return f"{simplified_content} [来源: {simple_file_name}]"
        
        # 未找到相关内容
        return f"未找到与'{query}'相关的信息，请尝试其他关键词。"

# 首页路由
@app.route('/')
def index():
    return render_template('index.html')

# 初始化知识库API路由
@app.route('/api/init', methods=['POST'])
def init_knowledge():
    try:
        success = initialize_knowledge()
        if success:
            message = f"知识库初始化成功！已加载 {len(knowledge_base)} 个知识库文件。"
            print(message)
            return jsonify({
                'status': 'success',
                'message': message,
                'files': [k['file'] for k in knowledge_base.values()]
            })
        else:
            error_msg = "知识库初始化失败，未找到有效的知识库文件。"
            print(error_msg)
            return jsonify({'status': 'error', 'message': error_msg})
    except Exception as e:
        error_msg = f"初始化知识库时发生错误: {str(e)}"
        print(error_msg)
        return jsonify({'status': 'error', 'message': error_msg}), 500

# 问答API路由
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': '问题不能为空，请输入您的问题。'})
        
        print(f"收到查询: '{query}'")
        
        # 处理查询并获取回答
        answer = process_query(query)
        
        print(f"生成回答: '{answer}'")
        
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"处理错误: {str(e)}")
        return jsonify({'error': '处理您的请求时发生错误，请稍后重试。'}), 500

# 初始化时尝试加载知识库
initialize_knowledge()

if __name__ == '__main__':
    app.run(debug=True, port=5000)