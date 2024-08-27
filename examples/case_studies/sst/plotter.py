import matplotlib.pyplot as plt
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np

class Plotter:
    def __init__(self, output_dir, ) -> None:
        self.output_dir = output_dir
        if not os.path.exists(f'{self.output_dir}'):
            os.mkdir(f'{self.output_dir}')
        self.linestyles = ['dashed', 'dashed', 'dashdot', 'dashdot', 'dashdot', 'solid', 'solid']
        self.colors = ['b', 'orange', 'MediumTurquoise', 'purple', 'g', 'r']
        self.markers = ['.', 's', 'x', 'o', 'v', '^']
                
    def plot_mlife_plot(self, metric_meas_period, error_m_life, tout_n_life, ser=0, trial=0, print_pdf=True):
        """
        The function `plot_mlife_plot` plots a graph with two y-axes, one for absolute error and one for turnout rate, and saves it as a PDF file.
        
        :param metric_meas_period: The parameter `metric_meas_period` is a list or array containing the time values (in milliseconds) at which the metric is measured
        :param error_m_life: The parameter `error_m_life` is an array that represents the absolute error values for a metric called `M_lifecycle` over a certain period of time
        :param tout_n_life: The parameter `tout_n_life` represents the turnout ratio for the lifecycle 
        :param ser: The parameter "ser" is used to specify the series number. It is an optional parameter that can be used to differentiate between different series of data or plots, defaults to 0 (optional)
        :param trial: The parameter "trial" represents the trial number. It is used to differentiate between different trials when saving the plot as a PDF file, defaults to 0 (optional)
        :param print_pdf: The `print_pdf` parameter is a boolean flag that determines whether or not to save the plot as a PDF file. defaults to True (optional)
        """
        metric_meas_period = np.divide(np.array(metric_meas_period, dtype=object), 1000)
        error_m_life = np.array(error_m_life, dtype=object)
        
        fig, (ax) = plt.subplots(1, 1, sharex=True, figsize=(12,5))        
        turnout_ratio = np.array(tout_n_life, dtype=object)

        title = r'$M_{lifecycle}$'
        max_value = np.nanmax(error_m_life)
        twinAxes = []
        paddingLeftAxis = 0.07 * max_value
        paddingRightAxis = 2
        
        ax.tick_params(axis='y', labelcolor="black", labelsize=30)
        ax.tick_params(axis='x', labelcolor="black", labelsize=30)
        ax.set_title(f'{title}', fontsize=25)
        ax.set_ylim(-paddingLeftAxis, max_value+paddingLeftAxis)
        twinAxes = ax.twinx()
        twinAxes.tick_params(axis='y', labelcolor="blue", labelsize=30)
        twinAxes.set_ylim(-paddingRightAxis, 100+paddingRightAxis)
        
        # Add x-axis label to the last subplot
        ax.set_xlabel(f"Time (s)", fontsize=30)
        ax.set_ylabel('Abs. Error (s)', color="k", fontsize=35)
   
        ax.scatter(metric_meas_period, error_m_life, color = 'red', s=100, marker='x', label="Error")
        twinAxes.scatter(metric_meas_period, turnout_ratio, color = 'royalblue', s=50, marker='.', label="Turnout Rate")

        steady_state_error = error_m_life[-5:]
        avg_steady_state_error = np.round(np.nanmean(steady_state_error), decimals=2)
        max_steady_state_error = np.round(np.nanmax(steady_state_error), decimals=2)
        min_steady_state_error = np.round(np.nanmin(steady_state_error), decimals=2)

        ax.axhline(y = avg_steady_state_error, xmin=0.75, color = 'k', linestyle = '-')
        ax.text(x=metric_meas_period[-1]*0.7, y=avg_steady_state_error+(0.035*avg_steady_state_error) , s=f"Avg:{avg_steady_state_error}", fontsize =10)
        ax.axhline(y = max_steady_state_error, xmin=0.75, color = 'g', linestyle = '--')
        ax.text(x=metric_meas_period[-1]*0.7, y=max_steady_state_error+(0.01*max_steady_state_error) , s=f"Max:{max_steady_state_error}", fontsize =10)
        ax.axhline(y = min_steady_state_error, xmin=0.75, color = 'g', linestyle = '--')
        ax.text(x=metric_meas_period[-1]*0.7, y=min_steady_state_error+(0.05*min_steady_state_error) , s=f"Min:{min_steady_state_error}", fontsize =10)

        ax.legend(loc='center left', fontsize=15, ncol=2)
        twinAxes.legend(loc='center right', fontsize=15, ncol=2)

        fig.tight_layout()
        n=0
        if print_pdf:
            if not os.path.exists(f'{self.output_dir}'):
                os.mkdir(f'{self.output_dir}')
            while True:
                n = n+1
                if(os.path.isfile(f'{self.output_dir}/mlife_errors_subplot_ser{ser}_trial_{trial}.pdf') == False):
                    plt.savefig(f'{self.output_dir}/mlife_errors_subplot_ser{ser}_trial_{trial}.pdf', dpi=300, format='pdf')
                    break

        plt.close()

    def plot_xseries_vs_sst(self, med_error, cis, labels, x_vals, print_pdf=True):
        """
        The function `plot_xseries_vs_sst` plots a line graph with confidence intervals comparing the median error values for different configurations against the average lifecycle ratio of a network.
        
        :param med_error: The `med_error` parameter is a 2D array that contains the median error values for each configuration. Each row represents a different configuration, and each column represents a different x value
        :param cis: The parameter "cis" is a 2D array that contains the confidence interval values for each configuration. The shape of the array is (num_configurations, num_x_values). Each row represents the confidence interval values for a specific configuration, and each column represents the confidence
        interval values for a specific x
        :param labels: The `labels` parameter is a list of strings that represents the labels for each line in the plot. Each string in the list corresponds to a different line in the plot
        :param x_vals: The x_vals parameter is a list of values that represent the x-axis values for the plot. These values will be used to label the x-axis ticks and determine the position of the data points on the x-axis
        :param print_pdf: The `print_pdf` parameter is a boolean value that determines whether or not to save the plot as a PDF file. If `print_pdf` is set to `True`, the plot will be saved as a PDF file. If `print_pdf` is set to `False`, the plot will not, defaults to True (optional)
        """
        fig, ax = plt.subplots(figsize=(10, 6))   
        x_vals = np.array(x_vals, dtype=float)          
        xticks_labels = np.array(x_vals, dtype=str) 
        ax.set_xticks(x_vals)
        ax.set_xticklabels(xticks_labels, rotation=45)
        for config in range(np.shape(med_error)[0]):
            median_vals = med_error[config] # median error values
            cis_vals = cis[config]   # confidence interval values
            line = ax.plot(x_vals, median_vals, linestyle=self.linestyles[config], marker=self.markers[config], markersize=7, label=labels[config], color=self.colors[config])
            lower_bound = np.subtract(median_vals, cis_vals)
            upper_bound = np.add(median_vals, cis_vals)
            ax.fill_between(x_vals, lower_bound, upper_bound, color=line[0].get_color(), alpha=0.3)

        ax.set_yscale('log')
        # We change the fontsize of minor ticks label 
        ax.tick_params(axis='both', which='major', labelsize=20)
        ax.tick_params(axis='both', which='minor', labelsize=8)        
        ax.set_xlabel("Average Lifecycle Ratio of Network", fontsize=20)
        ax.set_ylabel("Shared Sense of Time Error (s)", fontsize=20)

        ax.legend(loc='best', prop = { "size": 20 }, ncol=1)
        # Adjust the layout of the subplots
        fig.tight_layout()
        
        n=0
        if print_pdf:
            if not os.path.exists(f'{self.output_dir}'):
                os.mkdir(f'{self.output_dir}')
            while True:
                n = n+1
                if(os.path.isfile(f'lcr_error_{n}.pdf') == False):
                    plt.savefig(f'lcr_error_{n}.pdf', dpi=300, format='pdf')
                    break

        plt.close()
