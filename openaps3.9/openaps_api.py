import os
import json
import logging
from flask import Flask, request, jsonify
import threading
import time
from subprocess import call
from collections import namedtuple
from datetime import datetime, timezone
import datetime as dt
Action = namedtuple('ctrller_action', ['basal', 'bolus'])

logger = logging.getLogger(__name__)

app = Flask(__name__)
with open("./monitor/glucose.json") as f:
    data = json.load(f)
    f.close()

with open("./../glucosym/closed_loop_algorithm_samples/algo_input.json") as update_algo_input:
    loaded_algo_input = json.load(update_algo_input)
    update_algo_input.close()


@app.route('/policy', methods=['POST'])
def policy():
    """Main policy endpoint for OpenAPS controller decisions"""

    observations = request.get_json()
    glucose = observations.get('CGM', 120)
    cho = observations.get('CHO', 0)
    ind = observations.get('index', 0)
    print(f"Glucose: {glucose}, CHO: {cho}")
    data_to_prepend = data[0].copy()
    data_to_prepend["glucose"] = glucose
    data_to_prepend["date"] = int(time.time() * 1000) + ind * 5 * 60 * 1000
    data_to_prepend["dateString"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    data_to_prepend["noise"] = 0
    data_to_prepend["short_avgdelta"] = 0
    data_to_prepend["long_avgdelta"] = 0
    data_to_prepend["delta"] = 0

    print("data_to_prepend", data_to_prepend)
    data.insert(0, data_to_prepend)
    
   
    with open("./monitor/glucose.json", 'w') as outfile:
        json.dump(data, outfile, indent=4)
    
    tz = int(-(time.altzone if (time.daylight and time.localtime().tm_isdst > 0) else time.timezone)/3600) ## Time zone offset
    current_timestamp = dt.datetime.fromtimestamp(time.time()+0*60*60+ind*5*60).strftime('%Y-%m-%dT%H:%M:%S') ## Local time
    current_timestamp = current_timestamp + ("-" if tz<0 else "+") + str(abs(tz)).zfill(2) + ":00" ## Time zone offset appended

    with open('monitor/clock.json','w') as update_clock:
        json.dump(current_timestamp, update_clock)
   
    call(["openaps", "report", "invoke", "settings/profile.json"])
    call(["openaps", "report", "invoke", "monitor/iob.json"])
    
            #run openaps to get suggested tempbasal
    call(["openaps", "report", "invoke", "enact/suggested.json"])
    call(["cat", "enact/suggested.json"])


    with open("enact/suggested.json") as read_suggested:
        loaded_suggested_data = json.load(read_suggested)
        read_suggested.close()

    print(f"Suggested basal: {loaded_suggested_data['rate']}")
    action = Action(basal=loaded_suggested_data["rate"], bolus=0)
    return jsonify({"basal": action.basal, "bolus": action.bolus})

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True) 