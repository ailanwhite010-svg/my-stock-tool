import os
from fastapi import FastAPI, HTTPException
import tushare as ts

# --- 关键部分：检查环境变量 ---
# 从 Vercel 的环境变量中获取 Token
# 如果在本地测试，可以创建一个 .env 文件并写入 TUSHARE_TOKEN='你的token'
token = os.getenv('TUSHARE_TOKEN')

# 如果没有找到token，应用将无法启动，并给出明确提示
if not token:
    # 使用 HTTPException 在 FastAPI 启动时更容易调试
    # 但在 Vercel 环境下，更简单的方式是直接 raise 一个错误
    raise ValueError("错误：环境变量 TUSHARE_TOKEN 未设置或为空。请在 Vercel 项目设置中添加它。")

# 初始化 Tushare
ts.set_token(token)
pro = ts.pro_api()

# --- FastAPI 应用实例 ---
# Vercel 会自动寻找一个名为 "app" 的 FastAPI 实例
app = FastAPI()

# --- 根路由 (/) ---
# Vercel 的文件结构决定了 'api/index.py' 会处理 '/api' 路径下的请求
# 我们在这里定义一个 '/api' 根路径的响应，方便测试
@app.get("/api")
def read_root():
    return {"message": "欢迎使用股票查询工具 API！部署成功！"}

# --- 定义我们的工具路由 ---
# 注意：这里的路径是相对 '/api' 的，所以是 /query-stock
# 最终访问的 URL 是 https://your-app-name.vercel.app/api/query-stock
@app.get("/api/query-stock")
def query_stock(ts_code: str):
    """
    查询单个股票的日线行情数据。
    :param ts_code: 股票代码, 例如 '000001.SZ'
    :return: JSON格式的日线行情数据
    """
    try:
        df = pro.daily(ts_code=ts_code, limit=1)
        if df.empty:
            raise HTTPException(status_code=404, detail="未查询到该股票代码的数据")
        # 将DataFrame转换为JSON格式
        return df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询时发生内部错误: {str(e)}")

# FastAPI 会自动根据上面的代码生成 OpenAPI 文档
# 默认路径是 /openapi.json，Vercel 会将其映射到 /api/openapi.json
