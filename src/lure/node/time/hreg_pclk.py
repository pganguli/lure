from lure.config.configuration import Config
from lure.node.time.persistent_clock import PersistentClock

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from sklearn import linear_model 


class HarcRegPersistentClock(PersistentClock):
    def __init__(self, config: Config):
        super().__init__(config)
        self.batch = [10,23,40,60,100,120,145,155,170,200,260,np.shape(self.exp_data)[1]]
        self.batch_list = ["Batch0","Batch1","Batch2","Batch3","Batch4","Batch5","Batch6","Batch7","Batch8","Batch9","Batch10","Batch11"]

    def get_est_offtimes(self, input_off_time):    
        """
        The function `get_est_offtimes` takes an input off time, converts it to the appropriate units,
        calculates estimated times using trained models, and returns the estimated off time, maximum
        measurement, and maximum time measurement. The function `get_trained_SVM_model` is not shown in the
        code snippet.
        
        :param input_off_time: The input_off_time parameter is the off time measurement for which you want
        to estimate the estimated off time
        :return: three values: an integer representing the estimated off time, a float representing the
        maximum measurement, and a float representing the maximum time measurement.
        """
        input_off_times = []
        if self.time_units == "ms":
            input_off_times.append(np.divide(input_off_time, 1000))
        # Append an artificial large off-time to find out the max off-time measurement of harc-reg
        input_off_times = np.append(input_off_times, 1000)
        # input_off_times.append(1000)
        # Get voltage from the off time for test data
        comp_clk_est_time, harcLiteEstTime, maxMeasurementAllChannels, harcLiteMaxMeas =  self.cal_est_time_from_offtime(input_off_times, clk_type='harc-lite')
        # Get trained models
        svm_classifier, svm_scaler, trained_lasso_model = self.get_trained_models()
        pred_batches, testDataSVMScaled = self.predict_batch(svm_classifier_model=svm_classifier, scaler=svm_scaler, test_data=comp_clk_est_time)
        # Estimate off times using trained lasso model
        est_off_times, max_meas_list, max_time_meas = self.get_est_time_hreg(trained_lasso_model, comp_clk_est_time, pred_batches)
        if self.time_units == "ms":
            est_off_times = np.multiply(est_off_times, 1000)
        return int(est_off_times[0]), max_meas_list[0], max_time_meas

    def get_trained_SVM_model(self, est_time_exp_train, num_exp_train):
        """
        The function `get_trained_SVM_model` trains a Support Vector Machine (SVM) model using the provided
        training data and returns the trained model and a scaler object.
        
        :param est_time_exp_train: est_time_exp_train is a numpy array containing the training data. It has
        the shape (numSamples, numoffTime, numFeatures/Channels)
        :param num_exp_train: The parameter `num_exp_train` represents the number of experiments or samples
        in the training data
        :return: two objects: clf (SVM classifier) and scaler (StandardScaler).
        """
        exp_data_batches = []
        batch_ydata=[]            
        depend_var_num_min=0            
        i=0
        # Get all ylabels for the batches
        for n_batch in self.batch:  
            depend_var_num_max=n_batch
            for batch_n in range(depend_var_num_max-depend_var_num_min):
                batch_ydata.append(self.batch_list[i])
            depend_var_num_min=n_batch
            i=i+1
        depend_var_num_min=0
        depend_var_num_max=np.shape(est_time_exp_train)[1]
        # repeat ylabels for all samples/experiments
        exp_data_batches = np.tile(batch_ydata, num_exp_train)
        exp_data_batches = np.asarray(exp_data_batches, dtype=object)
        # Change shape of training data to (numSamples*numoffTime, numFeatures/Channels) -> this matches the training data with ylabels of batch numbers
        train_data = np.reshape(est_time_exp_train, (np.shape(est_time_exp_train)[0]*np.shape(est_time_exp_train)[1], np.shape(est_time_exp_train)[2]))
        exp_data_batches = np.asarray(exp_data_batches, dtype=object)
        exp_data_batches = exp_data_batches.flatten()
        # scale data using standard scaler
        scaler = StandardScaler()
        train_data_scaled = scaler.fit_transform(train_data)
        # Train SVM classifier
        clf = SVC(kernel='linear')
        clf.fit(train_data_scaled, exp_data_batches)

        return clf, scaler
 
    def get_trained_lassoreg_model(self, exp_data_train, est_time_exp_train, scale_data_flag = False):
        """
        The function `get_trained_lassoreg_model` trains a Lasso regression model on batches of data, with
        an option to scale the data before training.
        
        :param exp_data_train: exp_data_train is a numpy array containing the experimental data for training
        the model. It has the shape (num_samples, num_channels, num_features), where num_samples is the
        number of samples or experiments, num_channels is the number of channels or variables, and
        num_features is the number of features or
        :param est_time_exp_train: est_time_exp_train is a numpy array that contains the estimated off-times
        for each channel in each experiment (sample). The shape of est_time_exp_train is (num_samples,
        num_channels, num_estimated_times)
        :param scale_data_flag: The `scale_data_flag` parameter is a boolean flag that determines whether or
        not to scale the input data before training the model. If `scale_data_flag` is set to `True`, the
        input data will be scaled using the `StandardScaler` from scikit-learn before training the model,
        defaults to False (optional)
        :return: two lists: trained_model_batch and lasso_scaler_batch. trained_model_batch contains trained
        Lasso regression models for each batch, while lasso_scaler_batch contains the scalers used to scale
        the data for each batch (if scale_data_flag is True).
        """
        # Intialize the batches
        trained_model_batch = []
        lasso_scaler_batch = []
        batch_min = 0
        for n_batch in self.batch:
            batch_max = n_batch
            # Get off times and estimated off-times from each channel for each experiment (sample)
            all_exp_batch_offTimes = exp_data_train[:, batch_min:batch_max, 0].flatten()
            all_exp_batch_estTimes = est_time_exp_train[:, batch_min:batch_max, :]
            all_exp_batch_estTimes = np.reshape(all_exp_batch_estTimes, (np.shape(all_exp_batch_estTimes)[0]*np.shape(all_exp_batch_estTimes)[1], np.shape(all_exp_batch_estTimes)[2]))

            x_train_data_batch = all_exp_batch_estTimes
            y_train_data_batch = all_exp_batch_offTimes
            
            if scale_data_flag:
                model_aic = make_pipeline(StandardScaler(), linear_model.LassoLarsIC(criterion='aic', max_iter=100000))
                lasso_scaler = model_aic.named_steps['standardscaler']
                lasso_scaler_batch.append(lasso_scaler)
            else:
                model_aic = make_pipeline(linear_model.LassoLarsIC(criterion='aic', max_iter=100000))

            model_aic.fit(x_train_data_batch, y_train_data_batch)
            alpha = model_aic.named_steps['lassolarsic'].alpha_ 

            if (alpha != 0):
                model = linear_model.Lasso(alpha=alpha, max_iter=100000)
            else:
                model = linear_model.LinearRegression()

            trained_model = model.fit(x_train_data_batch, y_train_data_batch)
            trained_model_batch.append(trained_model)
            batch_min = batch_max

        return trained_model_batch, lasso_scaler_batch

    def get_trained_models(self):
        """
        The function `get_trained_models` extracts experiment data, calculates estimated times, and returns
        trained SVM and lasso regression models.
        :return: three objects: svm_classifier, svm_scaler, and trained_lasso_model.
        """
        # Extract experiment data from the file for training
        exp_data_train = self.exp_data
        # calculate estimated time for all channels for experiment data
        est_time_exp_train, num_exp_train = self.cal_est_times()
        # Get SVM classifier and predict batch numbers for each off-times
        svm_classifier, svm_scaler = self.get_trained_SVM_model(est_time_exp_train, num_exp_train)
        # Get trained lasso regression model
        trained_lasso_model, lassoScaler = self.get_trained_lassoreg_model(exp_data_train, est_time_exp_train)
        return svm_classifier, svm_scaler, trained_lasso_model

    def predict_batch(self, svm_classifier_model, scaler, test_data):
        """
        The function takes a SVM classifier model, a scaler, and test data as input, scales the test data
        using the scaler, predicts the labels for the scaled test data using the SVM classifier model, and
        returns the predicted labels and the scaled test data.
        
        :param svm_classifier_model: The svm_classifier_model parameter is the trained Support Vector
        Machine (SVM) classifier model that you want to use for making predictions on the test data
        :param scaler: The scaler is an object that is used to scale the test data. Scaling is a common
        preprocessing step in machine learning where the features are transformed to have a similar scale.
        This is important because many machine learning algorithms perform better when the features are on a
        similar scale
        :param test_data: The test_data parameter is the input data that you want to make predictions on
        using the SVM classifier model
        :return: two values: predicted_batch and test_data_scaled.
        """
        test_data_scaled = scaler.transform(test_data)
        predicted_batch = svm_classifier_model.predict(test_data_scaled)
        return predicted_batch, test_data_scaled


    def get_est_time_hreg(self, trained_model, comp_clk_est_time, predicted_batches):
        """
        The function `get_est_time_hreg` takes in a trained model, estimated completion clock time, and
        predicted batches, and returns the estimated off times, a list indicating if each batch is at the
        maximum measurement capability, and the maximum measurement capability.
        
        :param trained_model: The trained_model parameter is a list of trained machine learning models. Each
        model in the list is used to predict the estimated time for a specific batch
        :param comp_clk_est_time: The variable `comp_clk_est_time` is a list or array containing the
        estimated completion times for each batch. It is used as input to the trained model for prediction
        :param predicted_batches: The `predicted_batches` parameter is a list of batches that have been
        predicted by a model
        :return: three values: est_off_times, max_meas_list, and max_time_meas.
        """
        self.batch_list = np.array(self.batch_list, dtype=object)
        est_off_times = []
        max_meas_list = []
        idx = 0
        # Find out the max measurment capability
        max_time_meas = trained_model[-1].predict(comp_clk_est_time[-1].reshape(1, -1))[0]
        for batch in predicted_batches:
            batch_idx = np.where(self.batch_list == batch)[0][0]
            test_data = comp_clk_est_time[idx].reshape(1, -1)
            est_time = trained_model[batch_idx].predict(test_data)
            est_off_times.append(est_time[0])
            if est_time == max_time_meas:
                max_meas_list.append(True)
            else:
                max_meas_list.append(False)
            idx = idx + 1
        return est_off_times[0:-1], max_meas_list[0:-1], max_time_meas