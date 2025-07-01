import requests
import json
from collections import namedtuple
from datetime import datetime, timezone
Action = namedtuple('ctrller_action', ['basal', 'bolus'])

def test_openaps_api():
    """Test the OpenAPS API with different glucose values"""
    
    # API endpoint
    url = "http://127.0.0.1:5000/policy"
    
    # Test cases with different glucose values
    
    test_cases = [
        {"CGM": 200, "CHO": 0},    # Normal glucose
        # {"CGM": 180, "CHO": 0},    # High glucose
        # {"CGM": 80, "CHO": 0},     # Low glucose
        # {"CGM": 150, "CHO": 30},   # With carbohydrates
    ]
    
    print("Testing OpenAPS API...")
    print("=" * 50)
    
    for i, test_data in enumerate(test_cases):
        print(f"\nTest Case {i}:")
        print(f"Input: {test_data}")
        
        try:
            # Make POST request
            response = requests.post(url, json=test_data)
            
            if response.status_code == 200:
                # Parse the response and create Action object
                result_data = response.json()
                action = Action(basal=result_data["basal"], bolus=result_data["bolus"])
                print(f"Status: SUCCESS")
                print(f"Action: basal={action.basal}, bolus={action.bolus}")
            else:
                print(f"Status: ERROR (HTTP {response.status_code})")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("Status: ERROR - Could not connect to API")
            print("Make sure the Flask server is running on port 5000")
        except Exception as e:
            print(f"Status: ERROR - {str(e)}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_openaps_api()
