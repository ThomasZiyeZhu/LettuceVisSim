# Lettuce Growth Dynamic Simulation

A dynamic simulation system for lettuce growth that combines mechanistic modeling with Unity-based visualization. This project simulates lettuce growth under different environmental conditions and provides vadidated top-view canopy visual sensory data from unvalidated real-time 3D visualization.

## Features

- Mechanistic model for lettuce growth simulation
- Real-time 3D visualization using Unity
- ZeroMQ-based communication between Python and Unity
- Configurable parameters for growth simulation
- Support for different planting densities and environmental conditions

## Prerequisites
- Python 3.8 or higher
- Unity 2021.3 or higher (for development)
- ZeroMQ
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd LettuceGrowthDynamic
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Build Unity project:
   - Open the Unity project in Unity Editor
   - Build the project to the `LettuceRender` directory

## Project Structure

```
LettuceGrowthDynamic/
├── data/                      # Configuration and data files
│   ├── default_params.yaml    # Default simulation parameters
│   ├── optimal_params.json    # Optimized parameters
│   └── example_strategy.csv   # Example control strategy
├── LettuceRender/            # Unity build files
│   └── LettuceRender.exe     # Unity executable
├── log/                      # Log files
├── output_image/             # Generated images
├── base_lettuce_model.py     # Core growth model
├── net_comunication.py       # Unity communication
├── visual_function.py        # Visualization functions
└── simulation_example.py     # Example simulation script
```

## Usage

1. Run the simulation:
```bash
python simulation_example.py
```

2. The simulation will:
   - Start the Unity visualization
   - Load parameters from configuration files
   - Run the growth simulation
   - Generate visualization frames
   - Save output images

## Configuration

### Model Parameters
- Edit `data/default_params.yaml` to modify simulation parameters
- Edit `data/optimal_params.json` to update optimized parameters

### Visualization Settings
- Modify `visual_function.py` to adjust visualization parameters
- Adjust image dimensions in `net_comunication.py`

## Communication Protocol

The system uses ZeroMQ for communication between Python and Unity:
- Port: 5555 (default)
- Protocol: REQ-REP pattern
- Message format: JSON

## Output

The simulation generates:
- Real-time 3D visualization in Unity
- RGB and segmentation top-view canopy images in the `output_image` directory
- Console output with simulation progress

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact
ziye.zhu@wur.nl
