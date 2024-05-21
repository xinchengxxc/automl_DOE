#!/usr/bin/env python
# coding: utf-8

import os
import sys
import autosklearn.regression
import pandas as pd
import sklearn.metrics
from datetime import datetime


# #### measure resource consumption (start)
# # Get initial memory usage
# initial_memory = psutil.virtual_memory().used
# # Get initial CPU time
# initial_cpu_time = psutil.cpu_times().user + psutil.cpu_times().system

experiment = {
    'task_id': os.getenv('SLURM_ARRAY_TASK_ID'),
    'experiment_date_time': datetime.now().strftime("%Y-%m-%d_%H%M%S")
}

#### load experiment setup
def load_experiment_csv():
    # Load the CSV file into a DataFrame
    df = pd.read_csv("/workspaces/automl_DOE/Experiments/experiment_setup.csv")

    # Get a row by its index
    row_index = int(experiment['task_id'])
    row = df.iloc[row_index]

    return row.iloc[0], row.iloc[1], row.iloc[2]


#### main function
    
def run():
    # load simulation parameters from experiment list
    Model_dir, Traindata_name, Testdata_name = load_experiment_csv()

    rootpath = "/workspaces/automl_DOE"
    Database = rootpath + '/Modelbase'
    path = Database + '/' + Model_dir
    file_list = os.listdir(path)

    #test data
    Testdata = pd.read_csv(path + '/' + Testdata_name)
    X_test = Testdata.drop(['Z_mod'], axis=1)
    y_test = Testdata['Z_mod']
    
    #train data
    Traindata = pd.read_csv(path + '/' + Traindata_name)
    X_train = Traindata.drop(['Z_mod'], axis=1)
    y_train = Traindata['Z_mod']
#     n = Traindata.shape[0]
#     ratio = n/model_input
    #train model
    automl = autosklearn.regression.AutoSklearnRegressor(
        time_left_for_this_task = 180,
        per_run_time_limit = 30, # 20
        initial_configurations_via_metalearning=25,
        memory_limit=30000,
        resampling_strategy='cv',
        resampling_strategy_arguments={'folds':5},
        seed=12,
        n_jobs=1 # limit for parallel computation
    )
    automl.fit(X_train, y_train)
    #predict
    y_hat = automl.predict(X_test)
    #save the R2 score
#     R2 = automl.score(X_test, y_test)  ########
    R2=sklearn.metrics.r2_score(y_test, y_hat)
#     print("Test R2 score:", )
    #save the log
    log = automl.sprint_statistics()
    #create a new directory to save the results
    result_path = path + '/AutoML'
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    #save the results

    results = {
        "Model_dir": Model_dir,
        "Traindata_Name": Traindata_name,
        "R2_score": R2,
#         "Model_log": "string"
    }
    if os.path.exists(result_path+Traindata_name+".txt"):
        os.remove(result_path+Traindata_name+".txt")
        
    with open(result_path+Traindata_name+".txt", "a") as file:
        header = ",".join(results.keys()) + "\n"
        file.write(header)
        line = ",".join([str(value) for value in results.values()]) + "\n"
        # write in
        file.write(line)

#########
run()
