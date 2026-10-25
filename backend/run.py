"""
File khởi chạy máy chủ FastAPI Backend cho Hệ Thống Quản Lý Số Nhà (AppBienSoNha)
Chạy cổng 8000: http://127.0.0.1:8000
"""

import uvicorn
import os
import sys

# Thêm thư mục backend vào sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Đang khởi chạy Hệ Thống Quản Lý Số Nhà Tân Phú (FastAPI + Glassmorphism GIS)...")
    print("🌐 Truy cập Web UI tại: http://127.0.0.1:8000")
    print("📖 Swagger API Docs tại: http://127.0.0.1:8000/docs")
    print("🤖 MCP Gateway JSON-RPC tại: http://127.0.0.1:8000/mcp-gateway/rpc")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
