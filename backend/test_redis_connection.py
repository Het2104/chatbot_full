"""
Quick test script to verify Redis connection from Python
Run this before starting FastAPI to ensure Redis is accessible
"""

import redis
import sys

def test_redis_connection():
    print("\n" + "="*60)
    print("Testing Redis Connection")
    print("="*60)
    
    try:
        # Connect to Redis
        print("\n📡 Connecting to Redis at localhost:6379...")
        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Test PING
        print("   Sending PING...")
        response = r.ping()
        if response:
            print("   ✅ PING successful (PONG received)")
        else:
            print("   ❌ PING failed")
            return False
        
        # Test SET
        print("\n🔧 Testing cache operations...")
        print("   Setting test key...")
        r.set("test:python:connection", "Hello from Python!", ex=60)
        print("   ✅ SET successful")
        
        # Test GET
        print("   Getting test key...")
        value = r.get("test:python:connection")
        print(f"   ✅ GET successful: {value}")
        
        # Test TTL
        ttl = r.ttl("test:python:connection")
        print(f"   ⏰ TTL: {ttl} seconds")
        
        # Test DELETE
        print("   Deleting test key...")
        r.delete("test:python:connection")
        print("   ✅ DELETE successful")
        
        # Connection info
        info = r.info('server')
        print(f"\n📊 Redis Server Info:")
        print(f"   Version: {info.get('redis_version', 'Unknown')}")
        print(f"   Mode: {info.get('redis_mode', 'Unknown')}")
        print(f"   OS: {info.get('os', 'Unknown')}")
        
        stats = r.info('stats')
        print(f"\n📈 Stats:")
        print(f"   Total connections: {stats.get('total_connections_received', 0)}")
        print(f"   Total commands: {stats.get('total_commands_processed', 0)}")
        
        print("\n" + "="*60)
        print("✅ All Redis tests passed!")
        print("="*60)
        print("\n🚀 Redis is ready for FastAPI application")
        print("   You can now start the FastAPI server with:")
        print("   uvicorn app.main:app --reload\n")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if Redis is running: docker-compose ps redis")
        print("2. Check Redis logs: docker-compose logs redis")
        print("3. Restart Redis: docker-compose restart redis")
        return False
        
    except redis.TimeoutError as e:
        print(f"\n❌ Timeout Error: {e}")
        print("\nRedis is not responding. Check if it's running.")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
