import os
import tushare as ts
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json

# --- 配置区域 ---
# FastAPI应用实例
app = FastAPI(
    title="Dify Tushare Tool API",
    description="一个为Dify定制的、用于查询Tushare股票数据的增强版API工具。它会自动为股票代码添加.SH或.SZ后缀。",
    version="1.1",
)

# Tushare pro token
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "YOUR_DEFAULT_TOKEN_IF_ANY")
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# --- 数据模型定义 ---
class StockRequest(BaseModel):
    ticker: str = Field(..., description="要查询的6位A股股票代码（例如 '000001' 或 '600519'）")

# --- 辅助函数 ---
def get_suffix(stock_code):
    """根据股票代码首位判断并返回对应的交易所后缀"""
    if stock_code.startswith('6'):
        return '.SH'
    elif stock_code.startswith('0') or stock_code.startswith('3'):
        return '.SZ'
    else:
        return None # 或者可以返回一个默认值或抛出异常

# --- API端点 ---
@app.post("/api/get_stock_realtime_data", summary="获取股票实时行情和基础信息")
def get_stock_data(request: StockRequest):
    """
    根据提供的6位股票代码，查询该股票的实时行情、市值、市盈率等基本信息。
    API会自动判断并添加 '.SH' (上海) 或 '.SZ' (深圳) 后缀。
    """
    stock_code = request.ticker.strip()
    
    if not TUSHARE_TOKEN or TUSHARE_TOKEN == "YOUR_DEFAULT_TOKEN_IF_ANY":
        raise HTTPException(status_code=500, detail="服务器未配置TUSHARE_TOKEN环境变量")

    if len(stock_code) != 6 or not stock_code.isdigit():
        raise HTTPException(status_code=400, detail="请输入有效的6位数字股票代码。")

    suffix = get_suffix(stock_code)
    if not suffix:
        raise HTTPException(status_code=400, detail=f"无法识别的股票代码前缀: {stock_code}")

    ts_code = stock_code + suffix

    try:
        # 尝试获取数据
        df_basic = pro.daily_basic(ts_code=ts_code, fields='ts_code,trade_date,close,turnover_rate,volume_ratio,pe,total_mv')
        df_quote = pro.realtime_quote(ts_code=ts_code)

        if df_basic.empty and df_quote.empty:
            raise HTTPException(status_code=404, detail=f"未能查询到股票代码 {ts_code} 的任何数据，请检查代码是否正确或已上市。")

        # 合并结果
        result = {}
        if not df_basic.empty:
            latest_basic = df_basic.iloc[0].to_dict()
            result.update({
                "交易日期": latest_basic.get('trade_date'),
                "收盘价": latest_basic.get('close'),
                "换手率(%)": latest_basic.get('turnover_rate'),
                "量比": latest_basic.get('volume_ratio'),
                "市盈率(PE)": latest_basic.get('pe'),
                "总市值(万元)": latest_basic.get('total_mv'),
            })
        
        if not df_quote.empty:
            quote = df_quote.iloc[0].to_dict()
            result.update({
                "股票名称": quote.get('name'),
                "当前价": quote.get('price'),
                "开盘价": quote.get('open'),
                "最高价": quote.get('high'),
                "最低价": quote.get('low'),
                "昨日收盘价": quote.get('pre_close'),
                "成交量(手)": quote.get('volume'),
                "成交额(元)": quote.get('amount'),
            })
        
        # 使用json.dumps确保所有数据类型都可序列化，并转回dict
        return json.loads(json.dumps(result, allow_nan=False))

    except Exception as e:
        # 捕获Tushare本身可能抛出的异常或其他网络错误
        raise HTTPException(status_code=500, detail=f"查询过程中发生内部错误: {str(e)}")

# OpenAPI schema 端点，供Dify导入
@app.get("/api/openapi.json", summary="获取OpenAPI Schema")
def get_openapi_schema():
    return app.openapi()
