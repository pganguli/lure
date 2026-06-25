from lure.lure import Lure
from datetime import datetime

if __name__ == "__main__":
    now = datetime.now()

    for lmp_config in [2, 10, 30, 50]:
        simulator = Lure(
            config_dir="config-grid-r3xc3",
            top_config_file=f"lure_{lmp_config}.json",
            output_dir=f"output_sim_3x3_{lmp_config}",
            resume=True,
        )
        simulator.run()
