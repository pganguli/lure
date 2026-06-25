from lure.lure import Lure

if __name__ == "__main__":
    # Run Experiment
    simulator = Lure(
        config_dir="config",
        top_config_file="top.json",
        output_dir="output",
        resume=True,
        progress_bar=True,
    )
    simulator.run()
