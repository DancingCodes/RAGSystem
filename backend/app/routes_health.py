from __future__ import annotations  # 延迟解析类型注解
#
from fastapi import APIRouter  # 路由器
#
#
router = APIRouter()  # 创建路由器实例
#
#
@router.get("/api/health")  # 健康检查接口
def health():  # 健康检查处理函数
  return {"ok": True}  # 返回固定 OK

