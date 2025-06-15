import subprocess
import time
from pathlib import Path
import sys

# add project root directory to system path
root_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(root_dir))


import base_lettuce_model
import net_comunication
from visual_function import VisualFunction
import pandas as pd
import sys
from pathlib import Path
import yaml
from pathlib import Path
import matplotlib.pyplot as plt
import json
import time

# ============= Path settingup ===================
root_dir = Path(__file__).parent.absolute()
unity_executable_path = root_dir / "LettuceRender/LettuceRender.exe"
unity_log_path = root_dir / "log/unity_log.txt"


# ============= start unity backend ===================

print(f'[Python] Launching Unity executable from {unity_executable_path}')
unity_process = subprocess.Popen([
    str(unity_executable_path),
    "-batchmode",
    "-logFile", str(unity_log_path)
])
time.sleep(3) # wait for handshake


# ============== load parameters and action trajectory =============
default_parameters = root_dir / "data/default_params.yaml"
with open(default_parameters, 'r') as file:
    default_params = yaml.safe_load(file)

optimal_params = root_dir / "data/optimal_params.json"
with open(optimal_params, 'r') as file:
    optimal_params = json.load(file)

strategy_trajectory_path = root_dir / "data/example_strategy.csv"
strategy_trajectory = pd.read_csv(strategy_trajectory_path)
strategy_array = strategy_trajectory.values

# ============== initial lettuce dynamics and render controller ==================
lettuce_dry_weight_dynamic = base_lettuce_model.BaseLettuceMechanisticModel(
    plant_dw = 0.04,
    plant_density = 90,
    parameters = default_params
)

lettuce_dry_weight_dynamic.update_parameters(**optimal_params)

visual_function = VisualFunction( L = 10, W = 10)

unity_communication = net_comunication.UnityCommunication(
    ip = "127.0.0.1",
    port = 5555,
    save_dir = "output_image",
    image_width = 84,  # sensor output width
    image_height = 84  # sensor output height
)


if __name__ == "__main__":
    previous_hour_order = int(strategy_array[0, 6])
    data = visual_function.render_calculation(
        dw=lettuce_dry_weight_dynamic.state.sum(),
        plant_density=int(strategy_array[0, 3]),
        timestep=previous_hour_order
    )

    print("render the first frame")
    unity_communication.process_step(data)

    start_time = time.time()
    for i in range(len(strategy_array)):
        actions = strategy_array[i, :4]
        hour_order = int(strategy_array[i, 6])
        lettuce_dry_weight_dynamic.step(actions)

        if hour_order % 24 == 0 and hour_order != previous_hour_order:
            print(f'dw is {lettuce_dry_weight_dynamic.state.sum()} g per plant')
            print(f"hour_order changed from {previous_hour_order} to {hour_order}")
            current_day = hour_order // 24

            data = visual_function.render_calculation(
                dw=lettuce_dry_weight_dynamic.state.sum(),
                plant_density=int(actions[3]),
                timestep=hour_order,
                day=current_day
            )

            unity_communication.process_step(data)
            previous_hour_order = hour_order

    # ======= turn off unity =======
    try:
        unity_communication.shutdown()  # if shutdown() method is implemented
    except Exception as e:
        print(f"[Python] Shutdown failed or not implemented: {e}")
    finally:
        unity_communication.end_process()
        unity_process.terminate()

    end_time = time.time()
    print(f"total time: {end_time - start_time:.2f} seconds")
    print(f"total time: {(end_time - start_time)/60:.2f} minutes")

