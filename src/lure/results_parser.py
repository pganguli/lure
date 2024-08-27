from lure.results import ExperimentResult, SeriesResult, SimulationResult, LureResults
from lure.node.stats import Stats
from typing import Hashable, List

class ResultsParser():
    """A functionally static class that is used to parse the results provided by :py:meth:`lure.load_results` for the purposes of isolating data for plotting or other analysis.
    """

    @staticmethod
    def getExperiment(results: LureResults, exp_index: int) -> ExperimentResult:
        """Retrieve an ExperimentResult from a LureResults by index

        :param results: Data to be parsed
        :type results: LureResults
        :param exp_index: Index of desired experiment
        :type exp_index: int
        :return: The desired experiment
        :rtype: ExperimentResult
        """
        return results.experiment_results[exp_index]
      
    @staticmethod
    def getSeriesResultByIndex(experiment: ExperimentResult, series_index: int) -> SeriesResult:
        """Retrieve a SeriesResult object from an ExperimentResult by index

        :param experiment: Object to be parsed
        :type experiment: ExperimentResult
        :param series_index: Index of the desired series result
        :type series_index: int
        :return: The desired result
        :rtype: SeriesResult
        """
        series_vals = list(experiment.series_results.values())
        return series_vals[series_index]

    @staticmethod
    def getSeriesResultByMetadataKey(experiment: ExperimentResult, key: str) -> SeriesResult:
        """Retrieve a Series Result object from an ExperimentResult by its metadata key

        :param experiment: Object to be parsed
        :type experiment: ExperimentResult
        :param key: The metadata key corresponding to the desired series result
        :type key: str
        :raises Exception: For a key that does not exist
        :return: The desired result
        :rtype: SeriesResult
        """
        return experiment.series_results[key]  
  
    # @staticmethod
    # def getSeriesMetadata(experiment: ExperimentResult, series_index: int) -> DataSeriesMetadata:
    #     """Retrieves the metadata object by index

    #     :param experiment: Object to be parsed
    #     :type experiment: ExperimentResult
    #     :param series_index: The index corresponding to the DataSeriesMetadata, SeriesResult pair
    #     :type series_index: int
    #     :return: The desired metadata object
    #     :rtype: DataSeriesMetadata
    #     """
    #     series_metadata = list(experiment.keys())
    #     return series_metadata[series_index]
    
    @staticmethod
    def getNumTrials(experiment: ExperimentResult) -> int:
        """Returns the number of trials recorded in a particular experiment

        :param experiment: The experiment being examined
        :type experiment: ExperimentResult
        :return: The number of trials conducted in an experiment
        :rtype: int
        """
        series = ResultsParser.getSeriesResultByIndex(experiment, 0)
        xval1 = list(series.sim_results.keys())[0]
        all_trials = ResultsParser.getAllTrials(series_result=series, xval=xval1)
        return len(all_trials)

    @staticmethod
    def getAllXVals(experiment: ExperimentResult) -> List[Hashable]:
        """Retrieve all the x values associated with an experiement

        :param experiment: The experiment being parsed
        :type experiment: ExperimentResult
        :return: A list of x values
        :rtype: List[Hashable]
        """
        series_result = ResultsParser.getSeriesResultByIndex(experiment, 0)
        return series_result.x_values

    @staticmethod
    def getAllTrials(series_result: SeriesResult, xval: Hashable) -> List[SimulationResult]:
        """Retrieve all the trials of an experiment

        :param series_result: The series result being parsed
        :type series_result: SeriesResult
        :param xval: The key to a set of trials within a SeriesResult object
        :type xval: Hashable
        :return: A list of trial objects
        :rtype: List[SimulationResult]
        """
        return series_result.sim_results[xval]
    
    @staticmethod
    def getTrial(series_result: SeriesResult, xval: Hashable, trial_index: int) -> SimulationResult:
        """_summary_

        :param series_result: The series result being parsed
        :type series_result: SeriesResult
        :param xval: The key to a set of trials within a SeriesResult object
        :type xval: Hashable
        :param trial_index: The index of the desired trial
        :type trial_index: int
        :return: A list stat objects associated with a trial
        :rtype: SimulationResult
        """
        return (series_result.sim_results[xval])[trial_index]

    @staticmethod
    def getNode(trial: SimulationResult, node_id: int) -> Stats:
        """Retrieve a single stat object (node) from a trial

        :param trial: The trial being parsed
        :type trial: SimulationResult
        :param node_id: The node_id assigned to a node
        :type node_id: int
        :return: The stats object associated with a simulated node
        :rtype: Stats
        """
        with trial as s:
            return s[node_id]

    

