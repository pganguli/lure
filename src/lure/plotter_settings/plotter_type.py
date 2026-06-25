# Plotter configuration base class
import abc


# This interface covers plotting configurations for various experiment types/xtypes
# An xtype as a parameter should not be necessary because each config implementation is for a different xtype
class PlotterType(abc.ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "x_axis_vals")
            and callable(subclass.x_axis_vals)
            and hasattr(subclass, "plot_upper_bounds")
            and callable(subclass.plot_upper_bounds)
            and hasattr(subclass, "label_plot")
            and callable(subclass.label_plot)
            and hasattr(subclass, "save_plot")
            and callable(subclass.save_plot)
        )

    def x_axis_vals(self, ytype=None, x_to_graph=None):
        """
        Will configure and return a x_to_graph value that will be used to plot a single line
        """
        pass

    def plot_upper_bounds(self, plotter=None, ytype=None, experiment=None):
        """
        Plots upper bounds based upon the corresponding y type
        """
        pass

    def label_plot(self, experiment=None, ytype=None, num_simulations=0):
        """
        Sets the title as well as axis labels, limits, ticks, and scale
        """
        pass

    def save_plot(
        self,
        plotter=None,
        exp_index=0,
        ytype=None,
        skips_for_stabilization=0,
        data_type=None,
        percentile=None,
    ):
        """
        Save plot based on type and a boolean cutoff_for_stabilization value with a corresponding number
            of pkts to remove.
        """
        pass
