from fastapi import FastAPI, HTTPException
import os
import tushare as ts
import traceback  # 导入traceback库，用于格式化错误信息

# 创建一个空的 app 变量，我们稍后会填充它
app = None

# --- 关键的调试代码块 ---
try:
    # 尝试执行所有可能在启动时失败的代码
    print("--- Starting Application Initialization ---")

    # 1. 检查环境变量
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        # 如果没有token，我们主动抛出一个清晰的错误
        raise ValueError("CRITICAL: TUSHARE_TOKEN environment variable is not set or empty in Vercel project settings!")
    
    print(f"Successfully loaded TUSHARE_TOKEN starting with: {token[:4]}...")

    # 2. 尝试初始化 tushare
    ts.set_token(token)
    pro = ts.pro_api()
    print("Tushare pro_api initialized successfully.")

    # 3. 如果一切顺利，创建真正的FastAPI应用
    app = FastAPI(title="My Stock Tool API")
    print("FastAPI app created successfully.")

    @app.get("/api/health-check")
    def health_check():
        """
        一个简单的健康检查端点，确认应用是否正常运行。
        """
        return {"status": "ok", "message": "Application is running and Tushare is initialized."}

    @app.get("/api/test-data")
    def get_test_data():
        """
        尝试从Tushare获取少量数据，以验证连接。
        """
        data = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240105')
        return {"status": "success", "data": data.to_dict(orient='records')}

    print("--- Application Initialization Finished ---")


except Exception as e:
    # --- 如果上面 try 块中的任何一步失败，都会进入这里 ---
    print("---!!! FATAL ERROR DURING STARTUP !!!---")
    
    # 格式化完整的错误堆栈信息
    error_details = traceback.format_exc()
    
    # 在Vercel日志中打印这个详细错误
    print(error_details)
    
    print("--- Creating a fallback error reporting app ---")
    
    # 创建一个备用的、仅用于报告错误的 FastAPI 应用
    app = FastAPI()

    @app.get("/api/{full_path:path}")
    def report_startup_error(full_path: str):
        """
        捕获所有请求，并返回启动失败的详细错误信息。
        """
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Application failed to start. See traceback below.",
                "error_type": str(type(e).__name__),
                "error_message": str(e),
                "traceback": error_details.splitlines() # 将堆栈拆分成列表，更易读
            }
        )

