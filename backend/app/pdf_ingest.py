from __future__ import annotations  # 延迟解析类型注解
#
import re  # 正则处理文本
from typing import Iterable  # 可迭代返回类型
#
from pypdf import PdfReader  # 读取 PDF
#
#
_re_ws = re.compile(r"[ \t]+")  # 连续空格/Tab 归一化
_re_many_nl = re.compile(r"\n{3,}")  # 过多换行归一化
#
#
def extract_pdf_pages(path: str) -> list[tuple[int, str]]:  # 抽取 PDF 每页文本
  reader = PdfReader(path)  # 打开 PDF
  pages: list[tuple[int, str]] = []  # 存放 (页码, 文本)
  for i, page in enumerate(reader.pages, start=1):  # 遍历每一页并从 1 开始计数
    text = page.extract_text() or ""  # 提取文本（无则为空）
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # 统一换行符
    text = _re_ws.sub(" ", text)  # 压缩多余空白
    text = _re_many_nl.sub("\n\n", text).strip()  # 压缩过多空行并去首尾空白
    pages.append((i, text))  # 收集结果
  return pages  # 返回所有页
#
#
def chunk_text(  # 将整段文本切成多个 chunk
  text: str,  # 输入全文
  *,  # 之后必须用关键字传参
  target_size: int = 900,  # 目标 chunk 大小（字符）
  overlap: int = 120,  # chunk 之间重叠长度（字符）
) -> list[str]:  # 返回 chunk 列表
  if not text:  # 空文本直接返回
    return []  # 无 chunk
#
  paras = [p.strip() for p in text.split("\n\n") if p.strip()]  # 以段落双换行切分并清理
  if not paras:  # 没有有效段落
    return []  # 无 chunk
#
  chunks: list[str] = []  # 最终 chunk 列表
  buf: list[str] = []  # 当前缓冲段落
  cur_len = 0  # 当前缓冲长度
#
  def flush():  # 将缓冲区落成一个 chunk
    nonlocal buf, cur_len  # 修改外层变量
    if not buf:  # 缓冲为空
      return  # 无需处理
    chunk = "\n\n".join(buf).strip()  # 拼成 chunk 并清理
    if chunk:  # chunk 非空
      chunks.append(chunk)  # 加入结果
    buf = []  # 清空缓冲
    cur_len = 0  # 重置长度
#
  for p in paras:  # 逐段处理
    p_len = len(p)  # 当前段落长度
    if p_len > target_size:  # 段落过长
      flush()  # 先落盘之前缓冲
      for s in _split_long(p, target_size=target_size, overlap=overlap):  # 滑窗切分长段落
        chunks.append(s)  # 直接加入 chunk
      continue  # 处理下一个段落
#
    if cur_len + p_len + (2 if buf else 0) <= target_size:  # 加上段落后不超目标
      buf.append(p)  # 继续累积
      cur_len += p_len + (2 if buf else 0)  # 更新长度（含分隔符）
    else:  # 超出目标
      flush()  # 先落一个 chunk
      buf.append(p)  # 新 chunk 从当前段开始
      cur_len = p_len  # 重置长度
#
  flush()  # 处理尾部缓冲
  return _apply_overlap(chunks, overlap=overlap)  # 应用 overlap 拼接
#
#
def _split_long(text: str, *, target_size: int, overlap: int) -> Iterable[str]:  # 切分过长段落
  step = max(1, target_size - overlap)  # 计算滑动步长
  i = 0  # 起始索引
  n = len(text)  # 总长度
  while i < n:  # 直到遍历完成
    yield text[i : i + target_size].strip()  # 产出窗口片段
    i += step  # 前进步长
#
#
def _apply_overlap(chunks: list[str], *, overlap: int) -> list[str]:  # 把相邻 chunk 用尾部 overlap 拼起来
  if overlap <= 0 or len(chunks) <= 1:  # 不需要 overlap 或只有一个 chunk
    return chunks  # 直接返回
  out: list[str] = []  # 结果列表
  prev_tail = ""  # 上一个 chunk 的尾部
  for c in chunks:  # 逐个处理
    if prev_tail:  # 存在上一段尾部
      out.append((prev_tail + c).strip())  # 拼接后加入
    else:  # 第一个 chunk
      out.append(c)  # 原样加入
    prev_tail = c[-overlap:] if len(c) > overlap else c  # 更新尾部（不足则取全）
  return out  # 返回带 overlap 的 chunk
