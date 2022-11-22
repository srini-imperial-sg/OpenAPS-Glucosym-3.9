import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import f1_score
import sys
from subprocess import call
import time
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from sys import argv

#####################################################
Result_dir = "../../openaps_monitor/Reseult/" #update this position when the code dir changes
MITIGATION=1 #whether activate mitigation code 0:None; 1:TP; 2:FP; 3:TP+FP
Monitor = 3 #0:CAWT; 1:MPC 2:DT; 3: LSTM
if Monitor == 2:
	fps = np.load('../Reseult/script_jupyternotebook/results_fordt/DT_FPs_list.npy')
	tps = np.load('../Reseult/script_jupyternotebook/results_fordt/DT_TPs_list.npy')
##########################################################
initial_glucose = [80, 100, 120, 140, 160, 180]#, 200]
#initial_glucose = [80, 100]
#initial_glucose = [80]
cmd_main = 'python '+'updated_ct_script_iob_based.py '#change "updated_ct_script_iob_based_mitigation_CAWT" to this name before run it
# if MITIGATION>0:
# 	cmd_main = 'python '+'updated_ct_script_iob_based_mitigation_LSTM.py '
# cmd_main = 'python '+'updated_ct_script_iob_based_mitigation.py '#+sys.argv[1]  mitigate the unsafe action

scenario_inf=argv[1].replace('\n','')
scenario_num=int(scenario_inf.split('_')[0])
fault_num=int(argv[2])

test_resultL =pd.read_csv(Result_dir+f"script_jupyternotebook/PathRecovery/Simu0Out24_ResRecoveryD22-11-02.csv")
test_resultS =pd.read_csv(Result_dir+f"script_jupyternotebook/PathRecovery/Simu0Out6_ResRecoveryD22-11-02.csv")
df_testL = test_resultL[test_resultL['CV']==0]
df_testL = df_testL[df_testL['Mitigation']==True]
df_testL = df_testL[df_testL["filename"].str.contains(scenario_inf+f"/{fault_num}")]

df_testS = test_resultS[test_resultS['CV']==0]
df_testS = df_testS[df_testS['Mitigation']==True]
df_testS = df_testS[df_testS["filename"].str.contains(scenario_inf+f"/{fault_num}")]

if MITIGATION==0 or len(df_testL) or len(df_testS)>0:
	browser = webdriver.Firefox()
	browser.get("http://localhost:3000/")
	# input_text = browser.find_element_by_id("initialglucose") #
	input_text = browser.find_element(By.ID,"initialglucose")

	patient_name = ["patientA","patientB","patientC","patientD","patientE","patientF","patientG","patientH","patientI","patientJ"]
	#patient_name = ["patientA"]
	patient_id = 0

	# os.system('rm -r ./out/*') #clear the content in out folder 

	for i in browser.find_elements(By.XPATH,"//*[@type='radio']"):
		i.click()
		time.sleep(1)
		patient = patient_name[patient_id]
		if 1:#patient_id == 0:#0 or patient_id == 7:#9

			for fold in range(1): 

				if MITIGATION>0:
					
					file_testlist = np.load(Result_dir+"script_jupyternotebook/filelist/file_testlist_{}_CV{}.npy".format(patient,fold))
					test_resultS =pd.read_csv(Result_dir+f"script_jupyternotebook/PathRecovery/Simu0Out6_ResRecoveryD22-11-02.csv")
					test_resultL =pd.read_csv(Result_dir+f"script_jupyternotebook/PathRecovery/Simu0Out24_ResRecoveryD22-11-02.csv")

					df_testL = test_resultL[test_resultL['Patient']==patient]
					df_testL = df_testL[df_testL['CV']==fold]
					df_testS = test_resultS[test_resultS['Patient']==patient]
					df_testS = df_testS[df_testS['CV']==fold]

				for ig in initial_glucose:

					if MITIGATION>0:
						filename_test = '../simulationCollection_newmodel/{}/{}/{}/data_{}_{}.csv'.format(scenario_inf,fault_num,patient,patient,ig) #don't add "Result_dir+" here
						if not (filename_test in file_testlist):
							continue
						if Monitor == 2: #DT
							if MITIGATION ==1: #TP
								if not (filename_test in tps):
									continue
							elif MITIGATION ==2:
								if not (filename_test in fps): #only test FP cases: alert>0 and hazard==0
									continue

						else:
							
							unsafe_region = df_testL[df_testL["filename"]==filename_test]["Unsafe_Region"].tolist()[0]
							mitigationL = df_testL[df_testL["filename"]==filename_test]["Mitigation"].tolist()[0]
							mitigationS = df_testS[df_testS["filename"]==filename_test]["Mitigation"].tolist()[0]

							if MITIGATION ==1: #only test TP
								if not (unsafe_region == True and (mitigationL or mitigationS)) : 
									continue
							elif MITIGATION ==2: #only test FP cases: alert>0 and hazard==0
								if not (unsafe_region == False and (mitigationL or mitigationS)): 
									continue

							# #temporal code to only test BG<70 
							# df_file = pd.read_csv(Result_dir+filename_test[3:])
							# if (df_file["CGM_glucose"]<70).sum() <2:
							# 	continue 
							
						print('initial_glucose={}'.format(ig))

					# output_dir = 'out/'+patient+'/'+str(ig)+'/'
					# if os.path.isdir(output_dir) != True:
					# 	os.makedirs(output_dir)
					cmd_initialize = 'python '+'initialize.py '+ str(ig)
					input_text.clear()
					input_text.click()
					input_text.send_keys(str(ig))
					input_text.send_keys(Keys.RETURN)
					#time.sleep(1)
					os.system(cmd_initialize)
					os.system(cmd_main+' {} {}_CV{}  {}'.format(MITIGATION,patient,fold,Monitor))
					
					cmd_collect_data = 'python '+'updated_collected.py'
					os.system(cmd_collect_data)

					# cmd = 'cp -a out/alerts.txt out/fault_times.txt out/hazards.txt'  + ' ' + output_dir #annotated by zxg on AUG 14 2020
					# os.system(cmd)
						
					directory = "./simulation_data/"+patient
					
					if not os.path.exists(directory):
						os.makedirs(directory)
					
					csv_file_name = 'data_'+patient+'_'+str(ig)+'.csv'

					'''### use the independent update_riskindex.py under the Result folder to renew risk info### modified by zxg on AUG 14 2020 
					cm_file_name = 'confustion_matrix_'+str(ig)+'.txt'
					f1_file_name = 'f1_score_'+str(ig)+'.txt'
					cmd_label_data = 'python '+'data_labeling_script.py'
					os.system(cmd_label_data)
					
					
					data = pd.read_csv("labeled_data.csv", error_bad_lines=False)
					y_pred = np.array(data["detection"].tolist())
					y_true = np.array(data["Label"].tolist())
					
					#conf_matrix = confusion_matrix(y_true, y_pred)
					#print(conf_matrix)
					#print(classification_report(y_true, y_pred))
					
					writeFile_CM = open("confusion_matrix.txt", "w+")
					writeFile_F1 = open("f1_score.txt", "w+")
					writeFile_CM.write(np.array2string(confusion_matrix(y_true, y_pred)))
					#writeFile_F1.write(classification_report(y_true, y_pred))
					writeFile_F1.write(str(f1_score(y_true, y_pred,average=None)))
					cmd_move_conf_matrix = 'mv '+'confusion_matrix.txt '+directory+'/'+cm_file_name
					cmd_move_f1_score = 'mv '+'f1_score.txt '+directory+'/'+f1_file_name
					os.system(cmd_move_conf_matrix)
					os.system(cmd_move_f1_score)
					
					cmd_move_data = 'mv '+'labeled_data.csv '+directory+'/'+csv_file_name
					'''
					cmd_move_data = 'mv '+'data.csv '+directory+'/'+csv_file_name #use unlabeled data instead
					os.system(cmd_move_data)

		patient_id = patient_id+1	

	browser.close()
#**************************************************************
