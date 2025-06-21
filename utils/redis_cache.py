import redis
import json
from typing import Any, Optional
import os
from dotenv import load_dotenv 
from datetime import date 

# Custom JSON encoder to handle datetime.date objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat() # Convert date to ISO 8601 string
        return json.JSONEncoder.default(self, obj)

class RedisCache:
    """
    A simple wrapper for Redis caching.
    Now loads connection details from environment variables (e.g., .env file).
    Uses a custom JSON encoder for date serialization.
    """
    def __init__(self):
        load_dotenv()

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD")
        db = int(os.getenv("REDIS_DB", "0"))
        use_ssl = os.getenv("REDIS_USE_SSL", "False").lower() == "true"

        try:
            self.r = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=True,
                ssl=use_ssl,
                ssl_cert_reqs=None
            )
            self.r.ping()
            print(f"Connected to Redis cache at {host}:{port}/{db} (SSL: {use_ssl})")
        except redis.exceptions.ConnectionError as e:
            self.r = None
            print(f"Could not connect to Redis: {e}. Caching will be disabled.")
        except Exception as e:
            self.r = None
            print(f"An unexpected error occurred during Redis connection: {e}. Caching will be disabled.")


    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Sets a key-value pair in Redis.
        Args:
            key (str): The key to set.
            value (Any): The value to store. Will be JSON-serialized using CustomJSONEncoder.
            ex (Optional[int]): Expiration time in seconds (e.g., 3600 for 1 hour).
        Returns:
            bool: True if set successfully, False otherwise.
        """
        if not self.r:
            return False
        try:
            serialized_value = json.dumps(value, cls=CustomJSONEncoder)
            self.r.set(key, serialized_value, ex=ex)
            return True
        except Exception as e:
            print(f"Error setting cache key '{key}': {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from Redis.
        Args:
            key (str): The key to retrieve.
        Returns:
            Optional[Any]: The deserialized value if found, None otherwise.
        """
        if not self.r:
            return None
        try:
            serialized_value = self.r.get(key)
            if serialized_value:
                return json.loads(serialized_value)
            return None
        except Exception as e:
            print(f"Error getting cache key '{key}': {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        Deletes a key from Redis.
        """
        if not self.r:
            return False
        try:
            self.r.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting cache key '{key}': {e}")
            return False

if __name__ == "__main__":
    print("Testing RedisCache with .env loaded connection details and date serialization...")
    cache = RedisCache()
    if cache.r:
        test_key = "my_test_data_with_date"
        test_value = {"message": "Hello from Redis!", "today": date.today()}

        print(f"Setting '{test_key}' in cache with a date...")
        cache.set(test_key, test_value, ex=60)

        print(f"Getting '{test_key}' from cache...")
        retrieved_value = cache.get(test_key)
        print(f"Retrieved: {retrieved_value}")

        # Check if the retrieved value matches the expected structure
        # and contains today's date in ISO format
        if isinstance(retrieved_value, dict) and retrieved_value.get('today') == date.today().isoformat():
            print("Cache set and get with date successful!")
        else:
            print("Cache set and get with date failed or mismatch.")

        print(f"Deleting '{test_key}' from cache...")
        cache.delete(test_key)
    else:
        print("Redis cache not available, skipping test.")

        
# This code is a simple Redis cache implementation that loads connection details from environment variables,
# uses a custom JSON encoder to handle date serialization, and provides basic set, get, and delete methods.