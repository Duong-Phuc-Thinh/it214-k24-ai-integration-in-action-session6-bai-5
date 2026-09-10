import asyncio
import time
from typing import Optional
from fastapi import FastAPI, Query
import uvicorn
from pydantic import BaseModel

app = FastAPI(
    title="VietMart Dashboard API Aggregator",
    description="API Aggregator Pattern Demo with Async Call & Fallback Strategy",
    version="1.0.0"
)

class DashboardResponse(BaseModel):
    totalOrders: int
    weekRevenue: int
    activeProds: int
    newUsers: int
    executionTimeMs: float
    status: str = "SUCCESS"

# --- MOCK DOWNSTREAM SERVICES (Mô phỏng độ trễ 200ms cho từng service) ---
async def mock_get_total_orders() -> int:
    await asyncio.sleep(0.2)  # 200ms
    return 15200

async def mock_get_week_revenue() -> int:
    await asyncio.sleep(0.2)  # 200ms
    return 485000000

async def mock_get_active_products() -> int:
    await asyncio.sleep(0.2)  # 200ms
    return 3450

async def mock_get_new_users_this_month(should_fail: bool = False) -> int:
    await asyncio.sleep(0.2)  # 200ms
    if should_fail:
        raise ConnectionError("User Microservice timed out or unreachable!")
    return 1280

# --- HELPER WRAPPER DÙNG CHO FALLBACK & TIMEOUT TỪNG SERVICE ---
async def safe_execute(coro, default_value: int = 0, timeout_sec: float = 3.0) -> int:
    """
    Thực thi coroutine với timeout và fallback tự động nếu có lỗi (Graceful Degradation).
    Tương tự như exceptionally() trong CompletableFuture của Java.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_sec)
    except Exception as e:
        # Log lỗi hoặc ghi nhận metric giám sát tại đây
        print(f"[AGGREGATOR WARNING] Service call failed with error: {e}. Fallback value = {default_value}")
        return default_value

# --- ENDPOINT 1: CŨ - GỌI TUẦN TỰ (SLOW: ~800ms) ---
@app.get("/api/v1/dashboard/sequential", response_model=DashboardResponse)
async def get_dashboard_sequential(simulate_user_failure: bool = Query(False)):
    start_time = time.perf_counter()
    
    # 4 Lời gọi tuần tự (Sequential calls)
    try:
        total_orders = await mock_get_total_orders()
    except Exception:
        total_orders = 0
        
    try:
        week_revenue = await mock_get_week_revenue()
    except Exception:
        week_revenue = 0
        
    try:
        active_prods = await mock_get_active_products()
    except Exception:
        active_prods = 0
        
    try:
        new_users = await mock_get_new_users_this_month(should_fail=simulate_user_failure)
    except Exception:
        new_users = 0
        
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return DashboardResponse(
        totalOrders=total_orders,
        weekRevenue=week_revenue,
        activeProds=active_prods,
        newUsers=new_users,
        executionTimeMs=elapsed_ms,
        status="SEQUENTIAL_EXECUTION"
    )

# --- ENDPOINT 2: MỚI - API AGGREGATOR SONG SONG (FAST: ~200ms) ---
@app.get("/api/v1/dashboard/parallel", response_model=DashboardResponse)
async def get_dashboard_parallel(simulate_user_failure: bool = Query(False)):
    start_time = time.perf_counter()
    
    # Tạo các task bất đồng bộ chạy song song kèm fallback individual
    task_orders = safe_execute(mock_get_total_orders(), default_value=0)
    task_revenue = safe_execute(mock_get_week_revenue(), default_value=0)
    task_products = safe_execute(mock_get_active_products(), default_value=0)
    task_users = safe_execute(mock_get_new_users_this_month(should_fail=simulate_user_failure), default_value=0)
    
    # Tổng hợp tất cả kết quả song song với Timeout tổng 3.0 giây
    try:
        total_orders, week_revenue, active_prods, new_users = await asyncio.wait_for(
            asyncio.gather(task_orders, task_revenue, task_products, task_users),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        # Trường hợp cả cụm tổng hợp bị quá timeout 3s
        total_orders, week_revenue, active_prods, new_users = 0, 0, 0, 0

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return DashboardResponse(
        totalOrders=total_orders,
        weekRevenue=week_revenue,
        activeProds=active_prods,
        newUsers=new_users,
        executionTimeMs=elapsed_ms,
        status="PARALLEL_AGGREGATED"
    )

if __name__ == "__main__": 