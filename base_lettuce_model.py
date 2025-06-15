from typing import Dict, List, Tuple, Optional, Callable
import numpy as np
import numpy.typing as npt
from numba import jit
from pathlib import Path

@jit(nopython=True)
def _beer_lambert(lai: float, k: float) -> float:
    """Beer-Lambert law calculation with jit"""
    return -np.exp(-k * lai) + 1

@jit(nopython=True)
def _model_core(x, u, params_array, light_interception_method: int):
    """Core differential equations with jit
    
    Args:
        light_interception_method: Integer flag for method selection
            0: Beer-Lambert (default)
            1: External value (passed through params_array[-1])
    """
    t, r, co2, pd = u
    x = x * pd 
    # Unpack parameters (keep last element for external light interception)
    c_R, c_Q10_R = params_array[0:2]
    c_epsilon, c_w = params_array[2:4]
    g_bnd, g_stm = params_array[4:6]
    c_car_1, c_car_2, c_car_3 = params_array[6:9]
    c_gr_max, c_r = params_array[9:11]
    c_resp_sht, c_resp_rt = params_array[11:13]
    c_Q10_gr, c_Q10_resp = params_array[13:15]
    c_t, c_k, c_lar = params_array[15:18]
    c_a, c_b = params_array[18:20]
    external_li = params_array[20]  # External light interception if used
    # print(f"external_li: {float(external_li)}")
    # Calculate photosynthesis parameters
    R = c_R * c_Q10_R ** ((t - 20) / 10)
    lue = c_epsilon * (co2 - R) / (co2 + 2 * R)
    g_co2 = 1 / (1/g_bnd + 1/g_stm + 1/(c_car_1 * t**2 + c_car_2 * t + c_car_3))
    # Calculate light interception based on method
    if light_interception_method == 0:  # Beer-Lambert
        lai = c_lar * (1 - c_t) * x[1]
        light_interception = _beer_lambert(lai, c_k)
    else:  # External value
        light_interception = external_li
    # Rest of the calculations
    f_photo_max = ((lue * r * g_co2 * c_w * (co2 - R)) / 
                   (lue * r + g_co2 * c_w * (co2 - R)))
    f_photo = f_photo_max * light_interception
    
    rgr = (c_gr_max * (x[0] / (c_r * x[1] + x[0])) * 
           c_Q10_gr ** ((t - 20) / 10))
    f_resp = ((c_resp_sht * (1 - c_t) * x[1] + 
               c_resp_rt * c_t * x[1]) * 
              c_Q10_resp ** ((t - 25) / 10))
    
    ki = np.array([
        c_a * f_photo - rgr * x[1] - f_resp - 
        (1 - c_b) / c_b * rgr * x[1],
        rgr * x[1]
    ])
    
    return ki / pd

class BaseLettuceMechanisticModel:
    def __init__(self,
                 plant_dw: float,
                 plant_density: int,
                 parameters: Dict[str, float],
                 control_rate: int = 5,
                 light_interception_method: int = 0) -> None:
        
        
        '''
        light_interception_method: Integer flag for method selection
            0: Beer-Lambert (default)
            1: External value (passed through params_array[-1])
        '''
        
        self._validate_inputs(plant_dw, plant_density, parameters)
        self.parameters = parameters
        self.light_interception_method = light_interception_method
        self._external_light_interception = 0.0
        
        # Initialize state
        self.state0 = plant_dw
        self.state = np.array([self.state0 * 0.2, self.state0 * 0.8])
        self.h = control_rate * 60 # control rate in seconds, considering the 
        self.plant_density = plant_density
        
        # Initialize parameters array with space for external light interception
        self._init_params_array()

    def _init_params_array(self):
        """Convert parameters dictionary to array for Numba"""
        # 保持原有的参数顺序和转换方式
        self.params_array = np.array([
            self.parameters[k] for k in [
                'c_R', 'c_Q10_R', 'c_epsilon', 'c_w', 'g_bnd', 'g_stm',
                'c_car_1', 'c_car_2', 'c_car_3', 'c_gr_max', 'c_r',
                'c_resp_sht', 'c_resp_rt', 'c_Q10_gr', 'c_Q10_resp',
                'c_t', 'c_k', 'c_lar', 'c_a', 'c_b'
            ]
        ])
        # 添加外部光截获参数
        self.params_array = np.append(self.params_array, self._external_light_interception)

    def set_external_light_interception(self, value: float):
        """Set external light interception value"""
        if not 0 <= value <= 1:
            raise ValueError("Light interception must be between 0 and 1")
        self._external_light_interception = float(value)
        # 更新参数数组的最后一个元素
        # print(f"light_interception update: {value}")
        self.params_array[-1] = value

    def step(self, action: np.ndarray) -> None:
        """Advance model state by one timestep using RK4 method"""
        # Determine method flag
        
        method_flag = self.light_interception_method
        # print(f"method_flag: {method_flag}")
        # RK4 integration
        k1 = _model_core(self.state, action, self.params_array, method_flag)
        k2 = _model_core(self.state + self.h/2 * k1, action, self.params_array, method_flag)
        k3 = _model_core(self.state + self.h/2 * k2, action, self.params_array, method_flag)
        k4 = _model_core(self.state + self.h * k3, action, self.params_array, method_flag)
        
        self.state += self.h/6 * (k1 + 2*k2 + 2*k3 + k4) 

    def _validate_inputs(self, plant_dw: float, plant_density: int, parameters: Dict[str, float]) -> None:
        """Validate input parameters
        
        Args:
            plant_dw: Initial plant dry weight
            plant_density: Plant density
            parameters: Model parameters dictionary
        
        Raises:
            ValueError: If inputs are invalid
        """
        # 验证基本参数
        if plant_dw <= 0:
            raise ValueError("Plant dry weight must be positive")
        if plant_density <= 0:
            raise ValueError("Plant density must be positive")
            
        # 验证必需的参数是否存在
        required_params = {
            'c_a', 'c_b', 'c_gr_max', 'c_r', 'c_resp_sht', 'c_resp_rt',
            'c_Q10_gr', 'c_Q10_resp', 'c_t', 'c_k', 'c_lar', 'c_epsilon',
            'c_w', 'c_R', 'c_Q10_R', 'g_bnd', 'g_stm', 'c_car_1', 
            'c_car_2', 'c_car_3'
        }
        missing = required_params - set(parameters.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}") 

    def update_parameters(self, **new_params: Dict[str, float]) -> None:
        """Update model parameters during calibration
        
        Args:
            **new_params: Dictionary of parameters to update
                Keys must exist in current parameters
                Values must be within valid ranges
                
        Raises:
            ValueError: If parameters are invalid or unknown
        """
        # 验证参数是否存在
        unknown_params = set(new_params.keys()) - set(self.parameters.keys())
        if unknown_params:
            raise ValueError(f"Unknown parameters: {unknown_params}")
        
        
        # 更新参数字典
        self.parameters.update(new_params)
        
        # 重新初始化参数数组
        self._init_params_array() 
        
    def reset(self):
        """Reset model state to initial conditions"""
        self.state = np.array([self.state0 * 0.2, self.state0 * 0.8])
 
    