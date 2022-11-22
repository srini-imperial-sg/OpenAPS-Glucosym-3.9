import sys
# import json
import ujson as json
import datetime
from subprocess import call
#from datetime import datetime,timedelta
import time
import os
# from matplotlib import pyplot as plt
import random
from sys import argv
import tensorflow as tf
import numpy as np
from rrt import rrt_star

fault_injected = 0

openaps_rate = []
wrapper_rate = []
running_temp = []

track_increase = {"iteration": 0, "num_of_increase":0}
track_decrease = {"iteration": 0, "num_of_decrease":0}

gt_target_visit_stat = 0
lt_target_rising_visit_stat = 0
lt_target_falling_visit_stat = 0
init_iob_pointer = 0

unsafe_action_occurance = 0

faultIteration = random.randint(0,300)

##########################mitigation##################
Mitigation_Mode = False #reset initial status as normal mode
kMit = 0 #mitigation step pointer
Mitigation_Enable = int(argv[1])
threshold_col = argv[2]

x_test = [[]] 
# rl_bg = []
# rh_bg = []
# BGI_t1=0 #BGI[t-1]
# BGI_t2=0 #BGI[t-2]
if Mitigation_Enable:
  #====read threshold files############
  # thresholds=pd.read_csv("../Reseult/scripts-12rules/thresholds.csv")
  # threshold=thresholds[threshold_col]
  PredL_model = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_StateConstruction_12I_24O_Custom_model_"+str(threshold_col), compile=False)#patientJ_CV3
  PredS_model = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_StateConstruction_12I_6O_Custom_model_"+str(threshold_col), compile=False)#patientJ_CV3
  
  X2u_model   = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_x2u_6I_6O_Custom_model_"+str(threshold_col), compile=False)#patientJ_CV3

  # # PredL_model = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_StateConstruction_12I_24O_model_"+str(threshold_col), compile=False)#patientJ_CV3
  # # PredS_model = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_StateConstruction_12I_6O_model_"+str(threshold_col), compile=False)#patientJ_CV3
  # X2u_model   = tf.keras.models.load_model("../../openaps_monitor/Reseult/script_jupyternotebook/saved_model/LSTM128_x2u_6I_6O_model_"+str(threshold_col), compile=False)#patientJ_CV3

######################################################


#Input to the algo_bw.js. algo_bw.js format all the info and send to glucosym server. An algorithm is running in glucosym server that calculated next glucose and send the value back.
algo_input_list = {"index":0,"BGTarget":95,"sens":45,"deltat_v":20,"dia":4,"dt":5.0,"time":100000,"bioavail":6.0,"Vg":253.0,"IRss":1.3,"events":{"bolus":[{ "amt": 0.0, "start":0}],"basal":[{ "amt":0, "start":0,"length":0}],"carb":[{"amt":0.0,"start":0,"length":0},{"amt":0.0,"start":0,"length":0}]}}

#write the algo_input_list to a file named algo_input.json so that algo_bw.js can read the input from that file
with open("../glucosym/closed_loop_algorithm_samples/algo_input.json", "w") as write_algo_input_init:
  json.dump(algo_input_list, write_algo_input_init, indent=4)
  write_algo_input_init.close()


suggested_data_to_dump = {}
list_suggested_data_to_dump = []

#iteration_num = 5
iteration_num =150#200 #int(sys.argv[1])

#record the time 5 minutes ago, we need this time to attach with the recent glucose value
#time_5_minutes_back = ((time.time())*1000)-3000

############# added by xugui##########
reportHazardH1 = True
reportHazardH2 = True

'''Create files to record the outputs and alerts/hazards -- Xugui'''
output_dir = os.path.join(os.getcwd(), 'out')
hazard_file = output_dir + '/hazards.txt'
alert_file = output_dir + '/alerts.txt'
fault_file = output_dir + '/fault_times.txt'

hazardfile = open(hazard_file, 'w')
hazardfile.write('*********Hazards generated in this test run**********\n')

alertfile = open(alert_file, 'w')
alertfile.write('*********Alerts generated in this test run**********\n')
alertfile.close()

faultfile = open(fault_file, 'w')
faultfile.close()


for _ in range(iteration_num):

  glucose_refresh = True 
  rate_refresh = True # update the glucose reading and rate output command

  print("faultIteration: ", faultIteration)

  fault_prob = random.randint(1,100)
  
  with open("../glucosym/closed_loop_algorithm_samples/algo_input.json") as update_algo_input:
    loaded_algo_input = json.load(update_algo_input)
    update_algo_input.close()
    
  loaded_algo_input_copy = loaded_algo_input.copy()
  loaded_algo_input_copy['index'] = _
  
  #print(loaded_algo_input_copy)
  
  with open("monitor/glucose.json") as f:
    data = json.load(f)
  
  
  data_to_prepend = data[0].copy()

  
  read_glucose_from_glucosym = open("../glucosym/closed_loop_algorithm_samples/glucose_output_algo_bw.txt", "r")
  loaded_glucose = float(read_glucose_from_glucosym.read())

  ##### Detect Alerts #################
  # if float(loaded_glucose) > 280 or float(loaded_glucose) < 80:
  #   with open(alert_file, 'a+') as alertfile:
  #     alertfile.write('Alert|| Glucose = %s || Time(sec)=%s\n' % (loaded_glucose, _))

  ##### Detect Hyperglycemia (H1) -- added by Xugui
  if float(loaded_glucose) > 180:
    print ("Glucose id higher than 180!")
    if reportHazardH1 == True:
      hazardfile.write('HAZARD || H1 || Hyperglycemia || Time(sec)=%f\n' % (_))
      reportHazardH1 = False
    ##################

    ##### Detect Hypoglysimia (H2) -- added by Xugui
  if float(loaded_glucose) < 70:
    print ("Glucose id lower than 70!")
    if reportHazardH2 == True:
      hazardfile.write('HAZARD || H2 || Hypoglysimia || Time(sec)=%f\n' % (_))
      reportHazardH2 = False
    ##################

  # if glucose_refresh == True:
  prev_data_to_prepend_glucose = data_to_prepend["glucose"]
  data_to_prepend["glucose"] = loaded_glucose 

# Fault_injection ############# permanent hardware fault injection #################################  
  #glucose:HOOK#


  # if _ > 5:   
  #   data_to_prepend["glucose"] = 60
  #   fault_injected = fault_injected+1

  if glucose_refresh != True:
    data_to_prepend["glucose"] = prev_data_to_prepend_glucose 

################### End of permanent fault section #################

## Fault_injection ############## This section is for injecting intermittent fault with some probability #############
#  fault_prob = random.randint(1,100)
#
#  if fault_prob <=10:
#    ##data_to_prepend["glucose"] = random.randint(1,300)
#    data_to_prepend["glucose"] = 200.1111
#    fault_injected = fault_injected+1
#  else:
#    data_to_prepend["glucose"] = loaded_glucose

############### End of intermittend fault injection section ##########################

    
  data_to_prepend["date"] = int(time.time())*1000+(_)*5*60*1000 ##added (_)*5*60*1000
  
  data.insert(0, data_to_prepend)
  

  with open('monitor/glucose.json', 'w') as outfile:
    json.dump(data, outfile, indent=4)
    outfile.close()
  
  ##the following call will change the time of the system everytime, which is annoying; instead, a change will be made on the way calculating the current_timestamp
  ##call("date -Ins -s $(date -Ins -d '+5 minute')", shell=True)
    
  
  #current_timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S-07:00') ## Original
  #current_timestamp = datetime.datetime.fromtimestamp(time.time()+0*60*60+(_)*5*60).strftime('%Y-%m-%dT%H:%M:%S-04:00') ## After time change
  
  tz = int(-(time.altzone if (time.daylight and time.localtime().tm_isdst > 0) else time.timezone)/3600) ## Time zone offset
  current_timestamp = datetime.datetime.fromtimestamp(time.time()+0*60*60+(_)*5*60).strftime('%Y-%m-%dT%H:%M:%S') ## Local time
  current_timestamp = current_timestamp + ("-" if tz<0 else "+") + str(abs(tz)).zfill(2) + ":00" ## Time zone offset appended

  with open('monitor/clock.json','w') as update_clock:
    json.dump(current_timestamp, update_clock)

  
  
  call(["openaps", "report", "invoke", "settings/profile.json"])
  call(["openaps", "report", "invoke", "monitor/iob.json"])
  
        #run openaps to get suggested tempbasal
  
  call(["openaps", "report", "invoke", "enact/suggested.json"])
  call(["cat", "enact/suggested.json"])
  
#  current_timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S-07:00')
  
  #read the output in suggested.json and append it to list_suggested_data_to_dump list. Basically we are trying to get all the suggest      ed data and dump make a list lf that and then dump it to all_suggested.json file    
  with open("enact/suggested.json") as read_suggested:
    loaded_suggested_data = json.load(read_suggested)
    #list_suggested_data_to_dump.insert(0,loaded_suggested_data)
    #list_suggested_data_to_dump.append(loaded_suggested_data)
    read_suggested.close()

  loaded_suggested_data["loaded_glucose"] = loaded_glucose
  
#################################### Context table check #################################################################

  bg_target = 110
  
  if "IOB" in loaded_suggested_data:
    iob = loaded_suggested_data["IOB"]

  glucose = float(loaded_glucose)
    
  
  with open("monitor/temp_basal.json") as read_temp_basal:
    loaded_temp_basal = json.load(read_temp_basal)
    running_temp_rate = loaded_temp_basal ["rate"]

  loaded_suggested_data["running_temp"] = running_temp_rate

  #running_temp_rate = loaded_suggested_data["running_temp"]["rate"]
  
  # basal = loaded_suggested_data["basal"]
  
  if _ == 0:
    prev_glucose = glucose
  
  bg = loaded_suggested_data["bg"]  

  if glucose < 39:
    init_iob_pointer = 0
  else:
    init_iob_pointer = init_iob_pointer + 1

  if _ == 0 and glucose >= 39:
    prev_iob = iob
  
  elif init_iob_pointer == 1:
    prev_iob = iob

  if _ == 0:
    prev_rate = loaded_suggested_data["rate"]
  #del_rate = loaded_suggested_data["rate"] - running_temp_rate
  del_rate = loaded_suggested_data["rate"] - prev_rate
  del_bg = glucose - prev_glucose
  del_iob = iob - prev_iob
  
  ################# Context table 9th row (bg<70), zero_insulin must be delivered ########################
  
  if glucose >=39 and glucose < 75:
    if loaded_suggested_data["rate"] == 0:
      print("\n Safe_Action\n")
    else:
      loaded_suggested_data["fault"] = "yes"
      loaded_suggested_data["fault_reason"] = "row_38"  
      print("\n***************************************")
      print("********** Unsafe Action !!!!! *************")
      print("Reason: 39 =< glucose <=75; recommended rate is not zero")    
      print("***************************************\n")
      unsafe_action_occurance += 1

  ######################################## End of 9th row ######################################################################
  

####### Context table first and second row (bg>target and rising , iob is falling and stable)  ########################

  if glucose >= 75:
    #recommended_change_rate = loaded_suggested_data["rate"] - running_temp_rate
    print("\nprev_iob: ", prev_iob)
    print("iob: ", iob,"\n")
    print("\nprev_glucose: ", prev_glucose)
    print("loaded_glucose", glucose)
    print("\nbg\n", bg)
  
  if glucose >= 39:        
    prev_iob = iob
  
  prev_glucose = glucose

  x_test[0].append([glucose,iob,loaded_suggested_data["rate"]]) 
#########################=============inject fault here==============#####################
  ## Fault_injection : Injection of fault in Controller output ######################
  #rate:HOOK#
  if _>=6 and _<55:
    rate_refresh=0



  #loaded_suggested_data["rate"] = random.randint(0,5) # Activate for faulty system. For non_faulty system, comment this out 

  if rate_refresh != True:
    loaded_suggested_data["rate"] = prev_rate #only update rate output when rate_refresh equals to True


  #====================================================================================================================================#
  ################################################### mitigation code###################################################################
  if Mitigation_Enable:
    output_len = 6
    offset = 20
    bg_unsafe_H = 180 - offset
    bg_unsafe_L = 70 + offset
    #step1: state prediction
    if len(x_test[0])>12 and kMit%output_len == 0:
      yhatL = PredL_model.predict(np.array(x_test)[:,-12:]) #long prediction #shape (1,24,2)
      yhatS = PredS_model.predict(np.array(x_test)[:,-12:]) #short prediction #shape (1,6,2)

      bg_predL=yhatL[0][:,0]
      bg_predS=yhatS[0][:,0]

      if ((bg_predL>bg_unsafe_H).sum() + (bg_predL<bg_unsafe_L).sum() >1 or (bg_predS>bg_unsafe_H).sum() + (bg_predS<bg_unsafe_L).sum() >1): #two points in the unsafe region Xh
        Mitigation_Mode = True
        kMit = 0

        print(yhatL,yhatS)

        if (bg_predS<bg_unsafe_L).sum() >1 or (bg_predL<bg_unsafe_L).sum() >1:
          uc = np.zeros([output_len,1],dtype=float) 
        else:

          #Step 2: RRT
          if (bg_predS>bg_unsafe_H).sum() + (bg_predS<bg_unsafe_L).sum() >1: #quick mitigation
            path, T, t_conv = rrt_star(x0=[glucose,iob*100], num_iter=3000, delta=5, prev_state=[prev_glucose,prev_iob*100],constraints=[False])
          else:
            path, T, t_conv = rrt_star(x0=[glucose,iob*100], num_iter=3000, delta=5, prev_state=[prev_glucose,prev_iob*100])
          print(path)

          #Step 3: recovery action generation
          if len(path) < output_len: #x2u model takes input length of output_len=6
            path = path +[path[-1]]*(output_len-len(path)) #expand 
          path = np.array(path)
          path = np.c_[path[:,0],path[:,1]*0.01] #[BG,IOB/100]

          x2u_input = []
          for ipath in range(len(path)-output_len+1):
            x2u_input.append(path[ipath:ipath+output_len].tolist())
          uc   = X2u_model.predict(np.array(x2u_input)) #shape none*6*1
          uc = np.r_[uc[:-1,0],uc[-1]] #shape None*1
        uc = np.clip(uc,0,2.1) # [min,max]
        # uc   = X2u_model.predict(np.array(path).reshape(1,-1,2)[:,:output_len,:])
        print(uc,uc.shape)


    #step4: update control output
    if Mitigation_Mode:
      if (glucose<140 and glucose>120) or (kMit >= len(uc)): #stop mitigation after returning to the target region or "executed all the uc"
        Mitigation_Mode = False
        kMit = 0
      else: #mitigation
        #monitor error between path[t-1] and x[t]
        if kMit>0:
          # if np.any(abs(glucose-path[0][0])>[7,0.3]):
            #repeat step 2 and 3
            
            pass

        #replace control output
        loaded_suggested_data["rate"] = uc[kMit][0].astype(float) #shape=(1,6,1)
        # if glucose < 90:
        #   loaded_suggested_data["rate"] = 0
        kMit += 1 


  #================================================end of mitigation code####++=================================================================#
  ###############################################################################################################################################


  prev_rate = loaded_suggested_data["rate"]  

  list_suggested_data_to_dump.insert(0,loaded_suggested_data)
  #read the output in suggested.json and append it to list_suggested_data_to_dump list. Basically we are trying to get all the suggested data and dump make a list lf that and then dump it to all_suggested.json file    
  
  #################### Update pumphistory at very begining ##################
  if _==0:
    if  'duration' in loaded_suggested_data.keys():
    
      with open("monitor/pumphistory.json") as read_pump_history:
        loaded_pump_history = json.load(read_pump_history) # read whole pump_history.json
        pump_history_0 = loaded_pump_history[0].copy()  #load first element
        pump_history_1 = loaded_pump_history[1].copy() #load second element, fist and second are both for one temp basal
        pump_history_0['duration (min)'] = loaded_suggested_data['duration'] #update the values
        pump_history_1['rate'] = loaded_suggested_data['rate']
        pump_history_0['timestamp'] = current_timestamp
        pump_history_1['timestamp'] = current_timestamp

        loaded_pump_history.insert(0, pump_history_1) # insert second element back to whatever we loaded from pumphistory
        loaded_pump_history.insert(0, pump_history_0) #insert first element back to whatever we loaded from pumphistory
                      
        read_pump_history.close();
    
      with open("monitor/pumphistory.json", "w") as write_pump_history:
        json.dump(loaded_pump_history, write_pump_history, indent=4)
  
################ Update temp_basal.json with the current temp_basal rate and duration ####################
  
  #load temp_basal.json
  with open("monitor/temp_basal.json") as read_temp_basal:
    loaded_temp_basal = json.load(read_temp_basal)
    loaded_temp_basal['duration']-=5
    
    if loaded_temp_basal['duration']<=0:
      loaded_temp_basal['duration'] = 0
    
    if "doing nothing" not in loaded_suggested_data['reason']:

      if loaded_temp_basal['duration']==0:
        loaded_temp_basal['duration'] = loaded_suggested_data['duration']
        loaded_temp_basal['rate'] = loaded_suggested_data['rate']


        ######################### Update input of glucosym based on new temp ##############
        if loaded_suggested_data['rate'] == 0 and loaded_suggested_data['duration'] == 0:
          loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['basal']
          loaded_algo_input_copy["events"]['basal'][0]['length'] = 30
          loaded_algo_input_copy["events"]['basal'][0]['start'] = _*5
        else:
          
          loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['rate']
          loaded_algo_input_copy["events"]['basal'][0]['length'] = loaded_suggested_data['duration']
          loaded_algo_input_copy["events"]['basal'][0]['start'] = _*5
        
        ##################### Uppdate Pupmphistory ####################################
          
        with open("monitor/pumphistory.json") as read_pump_history:
          loaded_pump_history = json.load(read_pump_history) # read whole pump_history.json
          pump_history_0 = loaded_pump_history[0].copy()  #load first element
          pump_history_1 = loaded_pump_history[1].copy() #load second element, fist and second are both for one temp basal
          pump_history_0['duration (min)'] = loaded_suggested_data['duration'] # Activate for non_faulty system
          pump_history_1['rate'] = loaded_suggested_data['rate'] # Activate for non_faulty System
          pump_history_0['timestamp'] = current_timestamp
          pump_history_1['timestamp'] = current_timestamp

          loaded_pump_history.insert(0, pump_history_1) # insert second element back to whatever we loaded from pumphistory
          loaded_pump_history.insert(0, pump_history_0) #insert first element back to whatever we loaded from pumphistory
                        
          read_pump_history.close();
      
        with open("monitor/pumphistory.json", "w") as write_pump_history:
          json.dump(loaded_pump_history, write_pump_history, indent=4)
        
      
      else:  
        suggested_data_rate = loaded_suggested_data['rate'] #if "rate" in loaded_suggested_data else 0
        if loaded_temp_basal['rate']!=suggested_data_rate:
          loaded_temp_basal['rate']=suggested_data_rate
          loaded_temp_basal['duration']=loaded_suggested_data['duration'] #if "duration" in loaded_suggested_data else 0

          ####################### Update input of glucosym based on new temp ###########
          
          loaded_algo_input_copy["events"]['basal'][0]['amt'] = loaded_suggested_data['rate']
          loaded_algo_input_copy["events"]['basal'][0]['length'] = loaded_suggested_data['duration']
          loaded_algo_input_copy["events"]['basal'][0]['start'] = _*5

          #################### Uppdate Pumphistory ############################
          
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
    

#    else:
#      if loaded_temp_basal['duration']<=0:
#        loaded_temp_basal['duration'] = 0
    
    read_temp_basal.close()
  
  ## Fault_injection: Injection of fault in temp_basal ###############################
  
  ##temp_basal:HOOK##

  ############################### End of Fault injection #############################
    
  with open("monitor/temp_basal.json", "w") as write_temp_basal:
    json.dump(loaded_temp_basal, write_temp_basal, indent=4)    
      
  
  #print(suggested_data_to_dump)
  #write the list_suggested_data_to_dump into all_suggested.json file
  with open("enact/all_suggested.json", "w") as dump_suggested:
    json.dump(list_suggested_data_to_dump, dump_suggested, indent=4)
    dump_suggested.close()  

  #os.chdir("../glucosym/closed_loop_algorithm_samples")
  
  ####################### Write algo_input having the suggested output from openaps ##########################
  
  with open("../glucosym/closed_loop_algorithm_samples/algo_input.json", "w") as write_algo_input:
    json.dump(loaded_algo_input_copy, write_algo_input, indent=4)
  
  
  call(["node", "../glucosym/closed_loop_algorithm_samples/algo_bw.js"]);
  
    
hazardfile.close()

print("\n ########################################")
print("Fault injected: ", fault_injected)
print("Fault Occurrence:", unsafe_action_occurance, " times")
print("########################################\n")

