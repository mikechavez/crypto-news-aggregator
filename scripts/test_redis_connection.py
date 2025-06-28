import redis

def test_redis_connection():
    try:
        # Connect to Redis
        r = redis.Redis(
            host='grown-oarfish-27991.upstash.io',
            port=27991,
            password='AW1XAAIjcDExYTU4YWM2OGRkNzg0OThhYTkyM2YxNDhkOGM1ZmM2OXAxMA',
            ssl=True,
            socket_timeout=5  # 5 second timeout
        )
        
        # Test connection
        print("Testing Redis connection...")
        response = r.ping()
        
        if response:
            print("✅ Successfully connected to Redis!")
            
            # Test write/read
            test_key = "test:connection"
            test_value = "hello_upstash"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            
            if retrieved and retrieved.decode() == test_value:
                print(f"✅ Successfully wrote and read test value: {test_value}")
                r.delete(test_key)  # Clean up
                return True
            else:
                print("❌ Failed to read back test value")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_redis_connection()
