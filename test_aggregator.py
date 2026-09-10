from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_benchmark_and_tests():
    print("===========================================================")
    print("   VIETMART DASHBOARD API AGGREGATOR BENCHMARK TEST")
    print("===========================================================\n")
    
    # 1. Test Endpoint Tuần Tự (Sequential)
    print("[1/3] Calling Sequential Dashboard Endpoint (GET /dashboard/sequential)...")
    res_seq = client.get("/api/v1/dashboard/sequential")
    assert res_seq.status_code == 200
    data_seq = res_seq.json()
    print(f"      -> Latency: {data_seq['executionTimeMs']} ms")
    print(f"      -> Response: {data_seq}\n")
    
    # 2. Test Endpoint Song Song (Parallel Aggregator)
    print("[2/3] Calling Parallel Aggregator Dashboard Endpoint (GET /dashboard/parallel)...")
    res_par = client.get("/api/v1/dashboard/parallel")
    assert res_par.status_code == 200
    data_par = res_par.json()
    print(f"      -> Latency: {data_par['executionTimeMs']} ms")
    print(f"      -> Response: {data_par}\n")
    
    # 3. Test Resilience & Fallback khi UserService bị lỗi
    print("[3/3] Testing Fallback Handling (Simulating User Service Failure)...")
    res_fail = client.get("/api/v1/dashboard/parallel?simulate_user_failure=true")
    assert res_fail.status_code == 200
    data_fail = res_fail.json()
    print(f"      -> Latency: {data_fail['executionTimeMs']} ms")
    print(f"      -> Response: {data_fail}")
    print(f"      -> Fallback verification: newUsers = {data_fail['newUsers']} (Expected 0)\n")
    
    # Kiem tra Assertions
    assert data_seq["executionTimeMs"] >= 750, "Sequential execution must take ~800ms"
    assert data_par["executionTimeMs"] <= 300, "Parallel execution must finish within ~250ms"
    assert data_fail["newUsers"] == 0, "Failed service must return default fallback value 0"
    
    print("===========================================================")
    print(" SUCCESS: All Aggregator requirements passed perfectly!")
    print("===========================================================")

if __name__ == "__main__":
    run_benchmark_and_tests()
