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




@app.route('/policy', methods=['POST'])
def policy():
    """Main policy endpoint for OpenAPS controller decisions"""

    observations = request.get_json()
    glucose = observations.get('CGM', 120)
    cho = observations.get('CHO', 0)
    ind = observations.get('index', 0)
    
    with open("./../glucosym/closed_loop_algorithm_samples/algo_input.json") as f:
        loaded_algo_input = json.load(f)
        f.close()

    loaded_algo_input_copy = loaded_algo_input.copy()
    loaded_algo_input_copy['index'] = ind

    with open("./../glucosym/closed_loop_algorithm_samples/algo_input.json", 'w') as f:
        json.dump(loaded_algo_input_copy, f, indent=4)

    with open("./monitor/glucose.json") as f:
        data = json.load(f)
        f.close()
    
    data_to_prepend = data[0].copy()
    data_to_prepend["glucose"] = glucose
    data_to_prepend["date"] = int(time.time() * 1000) + ind * 5 * 60 * 1000 
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

    loaded_suggested_data['loaded_glucose'] = glucose

    if "IOB" in loaded_suggested_data:
        iob = loaded_suggested_data["IOB"]
   

    with open("monitor/temp_basal.json") as read_temp_basal:
        loaded_temp_basal = json.load(read_temp_basal)
        running_temp_rate = loaded_temp_basal["rate"]
    
    loaded_suggested_data['running_temp'] = running_temp_rate
    print(f"Suggested basal: {running_temp_rate}")

    if ind == 0:
        if 'duration' in loaded_suggested_data.keys():
            with open("monitor/pumphistory.json") as read_pump_history:
                loaded_pump_history = json.load(read_pump_history)
                pump_history_0 = loaded_pump_history[0].copy()
                pump_history_1 = loaded_pump_history[1].copy()
                pump_history_0['duration (min)'] = loaded_suggested_data['duration']
                pump_history_1['rate'] = loaded_suggested_data['rate']
                pump_history_0['timestamp'] = current_timestamp
                pump_history_1['timestamp'] = current_timestamp

                loaded_pump_history.insert(0, pump_history_1)
                loaded_pump_history.insert(0, pump_history_0)
                read_pump_history.close()
                
            with open("monitor/pumphistory.json", "w") as write_pump_history:
                json.dump(loaded_pump_history, write_pump_history, indent=4)
    
    with open("monitor/temp_basal.json") as read_temp_basal:
        loaded_temp_basal = json.load(read_temp_basal)
        loaded_temp_basal['duration']-=5
    
        if loaded_temp_basal['duration']<=0:
            loaded_temp_basal['duration'] = 0
    
        if "doing nothing" not in loaded_suggested_data['reason']:
            if loaded_temp_basal['duration']==0:
                loaded_temp_basal['duration'] = loaded_suggested_data['duration']
                loaded_temp_basal['rate'] = loaded_suggested_data['rate']

                if loaded_suggested_data['rate'] == 0 and loaded_suggested_data['duration'] == 0:
                    loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['basal']
                    loaded_algo_input_copy["events"]['basal'][0]['length'] = 30
                    loaded_algo_input_copy["events"]['basal'][0]['start'] = ind*5
                else:
                    loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['rate']
                    loaded_algo_input_copy["events"]['basal'][0]['length'] = loaded_suggested_data['duration']
                    loaded_algo_input_copy["events"]['basal'][0]['start'] = ind*5
                    
                with open("monitor/pumphistory.json") as read_pump_history:
                    loaded_pump_history = json.load(read_pump_history)
                    pump_history_0 = loaded_pump_history[0].copy()
                    pump_history_1 = loaded_pump_history[1].copy()
                    pump_history_0['duration (min)'] = loaded_suggested_data['duration']
                    pump_history_1['rate'] = loaded_suggested_data['rate']
                    pump_history_0['timestamp'] = current_timestamp
                    pump_history_1['timestamp'] = current_timestamp
                    loaded_pump_history.insert(0, pump_history_1)
                    loaded_pump_history.insert(0, pump_history_0)
                    read_pump_history.close();
                
                with open("monitor/pumphistory.json", "w") as write_pump_history:
                    json.dump(loaded_pump_history, write_pump_history, indent=4)
            else:
                suggested_data_rate = loaded_suggested_data['rate']
                if loaded_temp_basal['rate']!=suggested_data_rate:
                    loaded_temp_basal['rate']=suggested_data_rate
                    loaded_temp_basal['duration']=loaded_suggested_data['duration']
                    
                    loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['rate']
                    loaded_algo_input_copy["events"]['basal'][0]['length'] = loaded_suggested_data['duration']
                    loaded_algo_input_copy["events"]['basal'][0]['start'] = ind*5

                    with open("monitor/pumphistory.json") as read_pump_history:
                        loaded_pump_history = json.load(read_pump_history)
                        pump_history_0 = loaded_pump_history[0].copy()
                        pump_history_1 = loaded_pump_history[1].copy()
                        pump_history_0['duration (min)'] = loaded_suggested_data['duration']
                        pump_history_1['rate'] = loaded_suggested_data['rate']
                        pump_history_0['timestamp'] = current_timestamp
                        pump_history_1['timestamp'] = current_timestamp
                        loaded_pump_history.insert(0, pump_history_1)
                        loaded_pump_history.insert(0, pump_history_0)
                        read_pump_history.close();
                    
                    with open("monitor/pumphistory.json", "w") as write_pump_history:
                        json.dump(loaded_pump_history, write_pump_history, indent=4)

    read_temp_basal.close()

    with open("monitor/temp_basal.json", "w") as write_temp_basal:
        json.dump(loaded_temp_basal, write_temp_basal, indent=4)
    
    
    with open("./../glucosym/closed_loop_algorithm_samples/algo_input.json", 'w') as f:
        json.dump(loaded_algo_input_copy, f, indent=4)

    action = Action(basal=running_temp_rate, bolus=iob)
    return jsonify({"basal": action.basal, "bolus": action.bolus})

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True) 