'''
Take dw and plant density as input
Return json info for Unity
'''
import numpy as np
from numba import jit, njit, float64, int64

# 预编译参数数组，优化性能
PARAMS_SMALL = np.array([7.985305504553652, 291.73135988978663, -707.7401261511758, 772.4044195923515])
PARAMS_LARGE = np.array([30.9961439725485, 76.16800558950729, -6.5045717125301445, 0.26365904070466195])

@njit
def _3_degree_polynomial(x, params):
    return params[0] + x * (params[1] + x * (params[2] + x * params[3]))

@njit
def _calculate_scale(dw: float):
    '''
    unit of potential coverage is cm^2
    radius_based_scale unit is cm
    consider the unity space and unity scale unit is m or dm
    '''
    threshold = 0.3
    if dw < threshold:
        potential_coverage = _3_degree_polynomial(dw, PARAMS_SMALL)
    else:
        potential_coverage = _3_degree_polynomial(dw, PARAMS_LARGE)
    radiu_based_scale = np.sqrt(potential_coverage)
    return radiu_based_scale


@jit(nopython=True)
def _coordinate_calculation_vectorized(plant_density, L=10, W=10): 
    """Calculate grid-based coordinates that completely fill a rectangular area
    
    Args:
        plant_density: Base number of plants to distribute
        L: length of the field along X axis times 10
        W: width of the field along Z axis times 10
        
    Returns:
        tuple: (x_positions, z_positions) that completely fill the area
    """
    # add 20% of points to ensure full coverage in FOV
    target_points = int(plant_density * 1.2)
    
    # calculate the ratio of L and W    
    ratio = L / W
    
    # calculate the number of rows and columns based on the ratio
    # n_cols / n_rows should be close to ratio, and n_cols * n_rows >= target_points
    n_cols = int(np.sqrt(target_points * ratio))
    n_rows = int(np.sqrt(target_points / ratio))
    
    # ensure the product of n_cols and n_rows is at least equal to target_points
    while n_cols * n_rows < target_points:
        if n_cols / n_rows < ratio:
            n_cols += 1
        else:
            n_rows += 1
    
    # generate uniform distributed coordinates - remove endpoint parameter
    x_values = np.linspace(-L/2, L/2, n_cols)  # remove endpoint parameter
    z_values = np.linspace(-W/2, W/2, n_rows)  # remove endpoint parameter
    
    # create the result array
    total_grid_points = n_cols * n_rows
    x_positions = np.empty(total_grid_points, dtype=np.float64)
    z_positions = np.empty(total_grid_points, dtype=np.float64)
    
    # fill the coordinates
    idx = 0
    for z in z_values:
        x_positions[idx:idx+n_cols] = x_values
        z_positions[idx:idx+n_cols] = z
        idx += n_cols
    
    return x_positions, z_positions
    
    
class VisualFunction:
    def __init__(self,            
                 L = 0.1,
                 W = 0.1):
        # panel size for 1m^2
        self.L = L
        self.W = W
        # TODO, adding environment factors for illumination render in next step
    
    def render_calculation(self, dw, plant_density, timestep, day=0):
        print(f"view scale: {self.L} {self.W}")
        scale = _calculate_scale(dw)/6
        # upscale the scale to unity scale
        print(f"scale: {scale}")
        # develop a dw-based random function for scale, large dw, large random

        x_positions, z_positions = _coordinate_calculation_vectorized(plant_density, self.L, self.W)
        
        total_plant_number = len(x_positions)
        random_rotation = np.random.uniform(-40.0, 40.0, total_plant_number) #-10 to 10 is reasonable align with obervation
        random_scale = np.random.uniform(0.85, 1.15, total_plant_number) #0.95 to 1.1 is reasonable align with obervation
      # create the lettuce data in format for unity
        lettuces = []
        for i in range(total_plant_number):
            lettuce = {
                "id": i,
                "position": {
                    "x": float(x_positions[i]),
                    "y": 0,
                    "z": float(z_positions[i])
                },
                'rotation': float(random_rotation[i]),
                "scale": float(scale * random_scale[i])  # now is actual scale
            }
            lettuces.append(lettuce)
        
        data = {
            "lettuces": lettuces,
            "step": timestep,
            "day": day
        }
        
        #add debug info
        #print(f"[Python] Generated {len(lettuces)} lettuces")
        #print(f"[Python] Sample positions: {lettuces[0]['position'] if lettuces else 'No lettuces'}")
        
        return data

    
    
if __name__ == "__main__":
    # test the coordinate calculation
    plant_density = 100
    L = 1
    W = 1
    visual_function = VisualFunction(L, W)
    data = visual_function.render_calculation(0, plant_density, 0)
    print(data)
    dw = 0.04
    initial_state = 27.32074699 + 77.98493391 * dw - 6.69649276 * dw**2 + 0.26434308 * dw**3
    print(f"initial_state: {initial_state}")
    print(f"scale: {np.sqrt(initial_state)}")