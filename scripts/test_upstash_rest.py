import requests

def test_upstash_rest():
    url = "https://grown-oarfish-27991.upstash.io"
    headers = {
        "Authorization": "Bearer AW1XAAIjcDExYTU4YWM2OGRkNzg0OThhYTkyM2YxNDhkOGM1ZmM2OXAxMA",
        "Content-Type": "application/json"
    }
    
    # Test PING command
    response = requests.post(
        f"{url}/ping",
        headers=headers
    )
    
    print(f"PING Response: {response.status_code} - {response.text}")
    
    # Test SET command
    test_key = "test:connection"
    test_value = "hello_upstash"
    
    response = requests.post(
        f"{url}/set/{test_key}/{test_value}",
        headers=headers
    )
    
    print(f"SET Response: {response.status_code} - {response.text}")
    
    # Test GET command
    response = requests.get(
        f"{url}/get/{test_key}",
        headers=headers
    )
    
    print(f"GET Response: {response.status_code} - {response.text}")
    
    # Clean up
    response = requests.post(
        f"{url}/del/{test_key}",
        headers=headers
    )
    
    print(f"DEL Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_upstash_rest()
