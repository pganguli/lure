from lure.lure import Lure

if __name__ == "__main__":
    simulator = Lure(
        config_dir="config",
        top_config_file="lure.json",
        output_dir="output",
        resume=True,
        progress_bar=True,
    )
    simulator.run()
