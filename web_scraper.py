import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import hashlib
import difflib

def calculate_similarity(text1, text2):
    """计算两个文本的相似度"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def detect_similar_files(new_title, new_text, knowledge_dir, similarity_threshold=0.8):
    """检测相似的文件"""
    similar_files = []
    
    if not os.path.exists(knowledge_dir):
        return similar_files
    
    for filename in os.listdir(knowledge_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(knowledge_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                    
                    # 提取现有文件的标题和正文
                    existing_title_match = re.search(r'标题: (.*?)\n', existing_content)
                    existing_text_match = re.search(r'=== 正文内容 ===\n\n(.*)', existing_content, re.DOTALL)
                    
                    if existing_title_match and existing_text_match:
                        existing_title = existing_title_match.group(1).strip()
                        existing_text = existing_text_match.group(1)
                        
                        # 计算相似度
                        similarity = calculate_similarity(new_text, existing_text)
                        
                        if similarity >= similarity_threshold:
                            similar_files.append((filename, file_path, similarity, existing_title))
            except Exception as e:
                print(f"读取文件失败 {filename}: {e}")
    
    return similar_files

def extract_web_content(url):
    """从指定URL提取网页内容，优化标题提取和内容完整性"""
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=30)
        
        # 智能编码处理
        try:
            # 尝试根据响应头设置编码
            if 'charset' in response.headers.get('content-type', '').lower():
                response.encoding = response.apparent_encoding
            else:
                # 尝试UTF-8
                response.encoding = 'utf-8'
                # 验证编码是否正确
                response.text.encode('utf-8')
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试其他常见编码
            for encoding in ['gbk', 'gb2312', 'iso-8859-1']:
                try:
                    response.encoding = encoding
                    response.text.encode('utf-8')
                    break
                except UnicodeDecodeError:
                    continue
        
        if response.status_code != 200:
            print(f"请求失败: {response.status_code}")
            return None
        
        # 解析网页内容，使用lxml解析器提高效率
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取标题 - 优化标题提取策略
        title = "未知标题"
        # 优先尝试h1标签作为标题
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text(strip=True)
        # 如果没有h1或h1内容太短，使用title标签
        if not title or len(title) < 5:
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
        # 如果还是没有，尝试查找其他可能的标题元素
        if not title or len(title) < 5:
            meta_title = soup.find('meta', attrs={'name': 'title'})
            if meta_title and meta_title.get('content'):
                title = meta_title['content'].strip()
            else:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title = og_title['content'].strip()
        
        # 创建一个有序的内容收集列表，确保保留标题层级结构
        content_text = []
        
        # 首先尝试识别文档类内容结构（如培养方案、制度文件等）
        def extract_document_structure():
            # 查找可能的文档容器，优先考虑ID或class包含content、article等的div
            content_divs = soup.find_all('div', class_=re.compile(r'content|article|main|article-content|article_body|container|article-content'))
            content_divs += soup.find_all('div', id=re.compile(r'content|article|main|article-content|article_body'))
            
            # 如果找不到特定类的div，尝试查找section或article标签
            if not content_divs:
                content_divs = soup.find_all(['section', 'article'])
            
            # 如果还是找不到，使用body
            if not content_divs:
                content_divs = [soup.body]
            
            for content_div in content_divs:
                # 移除脚本、样式、导航等不相关元素
                for unwanted in content_div(['script', 'style', 'nav', 'footer', 'aside', 'form', 'iframe']):
                    unwanted.decompose()
                
                # 提取所有可能的标题和内容元素，保持顺序
                elements = content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section', 'li', 'span', 'table', 'tr', 'td'])
                
                # 收集有意义的文本内容
                collected_paragraphs = []
                current_text = ""
                
                for element in elements:
                    # 跳过空元素
                    text = element.get_text(strip=True)
                    if not text or len(text) < 3:  # 允许较短的文本，如章节编号
                        continue
                    
                    # 判断是否为标题元素
                    is_heading = element.name.startswith('h')
                    is_likely_heading = False
                    
                    # 检查是否可能是章节标题（如 "一、指导思想", "二、培养目标" 等格式）
                    if not is_heading:
                        # 检查是否以数字或汉字数字加标点开头
                        if re.match(r'^[一二三四五六七八九十百千]+[、\.]', text) or re.match(r'^\d+[\.、]', text):
                            # 判断是否为一级标题（可能是文档章节）
                            if len(text) < 50:  # 标题通常不会太长
                                is_likely_heading = True
                    
                    # 处理标题
                    if is_heading or is_likely_heading:
                        # 如果有累积的文本，先添加到集合
                        if current_text:
                            collected_paragraphs.append(current_text)
                            current_text = ""
                        
                        # 添加标题，根据级别添加前缀
                        if is_heading:
                            level = element.name
                            prefix = '#' * int(level[1]) + ' ' if level.startswith('h') else ''
                        else:
                            # 对于可能的章节标题，使用二级标题格式
                            prefix = '## '
                        
                        content_text.append(f"{prefix}{text}")
                    else:
                        # 合并段落内容，保留自然段落
                        if current_text:
                            current_text += ' ' + text
                        else:
                            current_text = text
                
                # 添加最后累积的文本
                if current_text:
                    collected_paragraphs.append(current_text)
                
                # 将收集的段落添加到内容中
                if collected_paragraphs:
                    for paragraph in collected_paragraphs:
                        # 分割过长的段落，保留句子结构
                        sentences = re.split(r'(\. |\? |! )', paragraph)
                        for i in range(0, len(sentences), 2):
                            if i + 1 < len(sentences):
                                content_text.append(sentences[i] + sentences[i+1])
                            else:
                                content_text.append(sentences[i])
                
                # 如果收集到足够内容，返回成功
                if len(content_text) > 5:  # 至少收集到5行有意义的内容
                    return True
            
            return False
        
        # 尝试提取文档结构
        found_structure = extract_document_structure()
        
        # 如果没有找到文档结构，尝试备用方法
        if not found_structure:
            # 提取页面所有文本，按自然段落组织
            all_text = []
            
            # 尝试查找主要内容区域
            main_content = None
            for selector in ['main', 'article', {'class': 'content'}, {'id': 'content'}]:
                if isinstance(selector, dict):
                    if 'class' in selector:
                        elements = soup.find_all(class_=selector['class'])
                    else:
                        elements = soup.find_all(id=selector['id'])
                    if elements:
                        main_content = elements[0]
                        break
                else:
                    element = soup.find(selector)
                    if element:
                        main_content = element
                        break
            
            # 如果找到主要内容，从中提取文本
            if main_content:
                for element in main_content.find_all(['p', 'div', 'li']):
                    text = element.get_text(strip=True)
                    if text and len(text) > 5:
                        all_text.append(text)
            else:
                # 否则从body提取所有段落
                for element in soup.body.find_all(['p', 'div']):
                    text = element.get_text(strip=True)
                    if text and len(text) > 10:  # 过滤掉较短的内容
                        all_text.append(text)
            
            # 添加到内容文本中
            content_text.extend(all_text)
        
        # 合并内容并清理
        full_content = '\n'.join(content_text)
        
        # 清理多余的空行，保留适当的段落分隔
        full_content = re.sub(r'\n\s*\n', '\n\n', full_content)
        # 移除多余的空格，但保留句子间的空格
        full_content = re.sub(r'\s+', ' ', full_content)
        # 重新添加适当的换行，尤其是在句号、问号、感叹号后
        full_content = re.sub(r'\.\s+(?!\d)', '.\n\n', full_content)  # 句号后加换行
        full_content = re.sub(r'\?\s+(?!\d)', '?\n\n', full_content)  # 问号后加换行
        full_content = re.sub(r'!\s+(?!\d)', '!\n\n', full_content)  # 感叹号后加换行
        
        # 确保标题行后面有换行
        full_content = re.sub(r'(#+\s+.+)', r'\1\n\n', full_content)
        
        # 对特殊格式的章节标题进行额外处理（如 "一、指导思想", "二、培养目标"）
        full_content = re.sub(r'(^|\n)([一二三四五六七八九十百千]+[、\.]\s*[^\n]+)', r'\1## \2', full_content)
        full_content = re.sub(r'(^|\n)(\d+[\.、]\s*[^\n]+)', r'\1### \2', full_content)
        
        return {
            'title': title,
            'content': full_content,
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"提取内容时出错: {str(e)}")
        return None

def save_to_knowledge(data, output_dir="knowledge", is_replace=False, original_file=None):
    """将提取的内容保存到knowledge文件夹"""
    if not data or not data['content']:
        print("没有可保存的内容")
        return False
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 如果是替换现有文件，使用与原始文件相同的名称（去掉时间戳部分）
    if is_replace and original_file and os.path.exists(original_file):
        # 保留原文件名但更新内容
        filename = original_file
    else:
        # 生成新文件名（基于标题和时间戳）
        # 先生成时间戳，确保在需要时可用
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. 首先确保标题不为空
        if not data['title'] or data['title'] == "未知标题":
            # 使用URL的最后部分作为标题
            url_parts = data['url'].split('/')
            # 查找包含内容的部分
            for part in reversed(url_parts):
                if part and part not in ['index.php', 'Home', 'content', 'id']:
                    data['title'] = part.replace('.html', '').replace('id=', '')
                    break
            if data['title'] == "未知标题":
                data['title'] = f"content_{timestamp}"
        
        # 2. 简化标题，移除多余的标点和空格
        # 移除多余的下划线和重复字符
        simplified_title = re.sub(r'_{2,}', '_', data['title'])
        # 移除末尾的特殊字符
        simplified_title = re.sub(r'[_\W]+$', '', simplified_title)
        
        # 3. 如果标题仍然过长，使用更智能的截断
        max_title_length = 30
        if len(simplified_title) > max_title_length:
            # 尝试在最后一个下划线处截断
            if '_' in simplified_title[:max_title_length]:
                # 找到最后一个下划线位置
                last_underscore = simplified_title[:max_title_length].rfind('_')
                simplified_title = simplified_title[:last_underscore]
            else:
                # 直接截断
                simplified_title = simplified_title[:max_title_length]
        
        # 4. 清理标题，只保留有意义的字符
        safe_title = re.sub(r'[^\w\u4e00-\u9fa5]', '_', simplified_title)
        
        # 5. 尝试从内容中提取主要主题
        main_topic = None
        content_lines = data['content'].strip().split('\n')
        
        # 1. 首先检查是否已经有类似"xxx本科人才培养方案"的完整主题
        for line in content_lines[:20]:  # 检查前20行
            line = line.strip()
            # 匹配完整的人才培养方案标题
            if '本科人才培养方案' in line or '专业人才培养方案' in line:
                # 提取方案名称
                match = re.search(r'[\u4e00-\u9fa5\w]+(?:本科|专业)人才培养方案', line)
                if match:
                    main_topic = match.group(0)
                    break
                else:
                    # 如果没找到完整匹配，使用整行作为主题
                    main_topic = line
                    break
            
            # 检查是否是专业名称行
            if re.search(r'[\u4e00-\u9fa5\w]+(?:专业|工程|科学)', line) and len(line) < 50:
                # 检查是否包含重要关键词
                keywords = ['人工智能', '物联网', '计算机', '数据科学', '软件工程', '电子信息']
                for keyword in keywords:
                    if keyword in line:
                        # 尝试提取更完整的主题
                        main_topic = line
                        break
                if main_topic:
                    break
        
        # 2. 如果没有找到完整主题，再尝试匹配章节标题
        if not main_topic:
            for line in content_lines[:10]:
                line = line.strip()
                if line:
                    # 匹配多种格式的章节标题
                    match = re.match(r'^([一二三四五六七八九十百千0-9]+[、章节卷]|\([一二三四五六七八九十百千0-9]+\))\s*([\u4e00-\u9fa5\w]+.*?)', line)
                    if match:
                        main_topic = match.group(2).strip()
                        break
        
        # 3. 处理并清理主题
        if main_topic:
            # 清理主题，确保文件名安全
            main_topic = re.sub(r'[^\w\u4e00-\u9fa5]', '_', main_topic)
            # 如果主题过长，适当截断
            if len(main_topic) > 50:
                main_topic = main_topic[:50]
            # 确保主题不为空且长度合理
            if len(main_topic) > 1:
                safe_title = main_topic
        
        # 6. 组合文件名（确保文件名不超过Windows限制）
        # Windows文件名限制为255字符，但我们保守一些
        max_filename_length = 200
        base_name = f"{safe_title}_{timestamp}.txt"
        
        # 如果文件名太长，进一步缩短标题部分
        if len(base_name) > max_filename_length:
            title_length = max_filename_length - len(f"_{timestamp}.txt")
            safe_title = safe_title[:title_length]
            base_name = f"{safe_title}_{timestamp}.txt"
        
        filename = os.path.join(output_dir, base_name)
    
    try:
        # 准备文件内容
        file_content = []
        file_content.append(f"标题: {data['title']}")
        file_content.append(f"来源: {data['url']}")
        file_content.append(f"提取时间: {data['timestamp']}")
        file_content.append("")
        file_content.append("=== 正文内容 ===")
        file_content.append("")
        file_content.append(data['content'])
        
        # 组合内容并确保编码正确
        full_content = '\n'.join(file_content)
        
        # 写入文件，明确指定UTF-8编码并添加BOM以确保Windows正确识别
        with open(filename, 'w', encoding='utf-8-sig') as f:
            f.write(full_content)
        
        print(f"内容已保存到: {filename}")
        return filename
    except Exception as e:
        print(f"保存文件时出错: {str(e)}")
        # 尝试备选保存方法
        try:
            # 使用二进制模式写入，确保编码正确
            with open(filename, 'wb') as f:
                f.write(full_content.encode('utf-8-sig'))
            print(f"使用二进制模式成功保存: {filename}")
            return filename
        except Exception as inner_e:
            print(f"二进制模式保存也失败: {str(inner_e)}")
            return False

def main():
    """主函数，读取URL列表并处理"""
    # 从文件中读取URL
    url_file = "网址.txt"
    output_dir = "knowledge"
    urls = []
    success_count = 0
    
    try:
        # 尝试读取URL文件，如果不存在则使用示例URL
        if os.path.exists(url_file):
            with open(url_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
        
        # 如果文件中没有URL或文件不存在，使用示例URL
        if not urls:
            print(f"{url_file} 文件中没有找到有效的URL或文件不存在，使用示例URL")
            urls = ["https://www.kmcc.edu.cn/index.php/Home/Sjkxygcxy/content/id/40644.html"]
        
        print(f"开始从 {len(urls)} 个URL提取内容...")
        
        for url in urls:
            print(f"\n正在处理: {url}")
            data = extract_web_content(url)
            
            if data:
                # 对于特定的培养方案页面，直接从页面提取所需内容
                print("检测到页面，进行专门处理...")
                # 重新请求页面，确保获取完整的HTML
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept-Encoding': 'gzip, deflate, br'
                    }
                    response = requests.get(url, headers=headers, timeout=30)
                    
                    # 智能编码处理
                    try:
                        if 'charset' in response.headers.get('content-type', '').lower():
                            response.encoding = response.apparent_encoding
                        else:
                            response.encoding = 'utf-8'
                            response.text.encode('utf-8')
                    except UnicodeDecodeError:
                        for encoding in ['gbk', 'gb2312', 'iso-8859-1']:
                            try:
                                response.encoding = encoding
                                response.text.encode('utf-8')
                                break
                            except UnicodeDecodeError:
                                continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # 直接提取所有段落和标题内容
                    all_text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
                    main_content = []
                    
                    for element in all_text_elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 5:  # 保留有一定长度的文本
                            # 对标题进行特殊标记
                            if element.name.startswith('h'):
                                level = int(element.name[1])
                                prefix = '#' * level + ' '
                                main_content.append(prefix + text)
                            else:
                                main_content.append(text)
                    
                    # 如果找到内容，替换原来的内容
                    if main_content:
                        data['content'] = '\n\n'.join(main_content)
                        print("已提取页面内容")
                except Exception as e:
                    print(f"提取内容时出错: {str(e)}")
            
                # 检查是否有相似的文件
                similar_files = detect_similar_files(data['title'], data['content'], output_dir)
                
                if similar_files:
                    # 按照相似度排序，选择最相似的文件
                    similar_files.sort(key=lambda x: x[2], reverse=True)
                    most_similar = similar_files[0]
                    filename, file_path, similarity, existing_title = most_similar
                        
                    print(f"检测到相似内容: {filename} (相似度: {similarity:.2f})")
                    print(f"  现有标题: {existing_title}")
                    print(f"  新标题: {data['title']}")
                        
                    # 注意：使用新的文件名生成逻辑，而不是替换现有文件
                    print("将使用新文件名保存内容")
                    saved_file = save_to_knowledge(data, output_dir)
                else:
                    # 保存为新文件
                    saved_file = save_to_knowledge(data, output_dir)
                
                if saved_file:
                    success_count += 1
            else:
                print(f"从 {url} 提取内容失败")
        
        print(f"\n提取完成！成功处理了 {success_count}/{len(urls)} 个URL")
        
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        # 确保即使出错也能输出完成信息
        if 'urls' in locals():
            print(f"\n提取完成！成功处理了 {success_count}/{len(urls)} 个URL")
        else:
            print("\n提取完成！但未处理任何URL")

if __name__ == "__main__":
    main()