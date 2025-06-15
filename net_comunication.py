import zmq
import base64
from PIL import Image
import io
import os 
import json
import time


class UnityCommunication:
    
    def __init__(self, ip = "127.0.0.1", 
                 port = 5555, 
                 save_dir = "output_image",
                 image_width = 512,
                 image_height = 512):
        self.unity_ip = ip
        self.unity_port = port
        self.save_dir = save_dir
        self.image_width = image_width
        self.image_height = image_height
        
        # check or create the save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        # ============ zeromq config ============
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.unity_ip}:{self.unity_port}")
        print(f"Python connected to unity zeromq sever at {self.unity_ip}:{self.unity_port}")
        
        # perform handshake and initialize
        self.perform_handshake()
        self.initialize_unity()
        
    def perform_handshake(self):
        """perform handshake with unity"""
        max_retries = 10
        retry_delay = 1.0  # second
        
        for attempt in range(max_retries):
            try:
                print(f"[Python] Attempting handshake (attempt {attempt + 1}/{max_retries})...")
                
                # send handshake request
                handshake_data = {
                    "message_type": "handshake"
                }
                
                self.socket.send_string(json.dumps(handshake_data))
                
                # 设置接收超时
                self.socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3秒超时
                
                try:
                    response_str = self.socket.recv_string()
                    response = json.loads(response_str)
                    
                    if response.get('status') == 'success' or response.get('status') == 'ok':
                        print(f"[Python] Handshake successful: {response.get('message', 'Connected')}")
                        # clear timeout setting
                        self.socket.setsockopt(zmq.RCVTIMEO, -1)
                        return
                    else:
                        print(f"[Python] Handshake failed: {response}")
                        
                except zmq.Again:
                    print(f"[Python] Handshake timeout on attempt {attempt + 1}")
                    
            except Exception as e:
                print(f"[Python] Handshake error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                print(f"[Python] Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
        
        # 清除超时设置
        self.socket.setsockopt(zmq.RCVTIMEO, -1)
        raise RuntimeError('Unity handshake failed after all attempts')
        
    def initialize_unity(self):
        """发送初始化配置到Unity，包括图片尺寸设置"""
        config_data = {
            "message_type": "initialize",
            "image_width": self.image_width,
            "image_height": self.image_height
        }
        
        print(f"[Python] Sending initialization config: {self.image_width}x{self.image_height}")
        self.socket.send_string(json.dumps(config_data))
        response_str = self.socket.recv_string()
        response = json.loads(response_str)
        
        if response.get('status') == 'success':
            print(f"[Python] Unity initialized successfully with image size: {self.image_width}x{self.image_height}")
        else:
            print(f"[Python] Unity initialization failed: {response.get('message', 'Unknown error')}")
            
    def process_step(self, step_data):
        # 为仿真数据添加消息类型标识
        step_data["message_type"] = "simulation"
        
        self.socket.send_string(json.dumps(step_data))
        response_str = self.socket.recv_string()
        print(f"[Python] Received response string length: {len(response_str)}")
        print(f"[Python] Raw response (first 200 chars): {response_str[:200]}")
        response = json.loads(response_str)
        self._check_response(response)
        self.save_image(response)
        
    
    def _check_response(self, response):
        '''
        check the response from unity, is it has image data
        response_str is a dict from json.loads(response_str)
        '''
        try:
            print(f"[Python] Response status: {response.get('status')}")
            print(f"[Python] Response keys: {list(response.keys())}")
            if 'rgb' in response:
                print(f"[Python] RGB image data length: {len(response['rgb'])}")
            else:
                print("[Python] No RGB image data in response")
            if 'segmentation' in response:
                print(f"[Python] Segmentation image data length: {len(response['segmentation'])}")
            else:
                print("[Python] No segmentation image data in response")  
                
            if response.get('status') != 'success':
                print(f"[Python] Full response: {response}")    
        except Exception as e:
            print(f"Error checking response: {e}")
            return None
        
        
    def save_image(self, response):
        '''
        save image data for checking
        two types of image:rgb and segmentation
        response is a dict from json.loads(response_str)
        '''
        rgb_image = base64.b64decode(response['rgb'])
        rgb_image = Image.open(io.BytesIO(rgb_image))
        rgb_image.save(os.path.join(self.save_dir, f"step_{response['step']}_rgb.png"))
        
        segmentation_image = base64.b64decode(response['segmentation'])
        segmentation_image = Image.open(io.BytesIO(segmentation_image))
        segmentation_image.save(os.path.join(self.save_dir, f"step_{response['step']}_segmentation.png"))
        
    def shutdown(self):
        """Gracefully shutdown the Unity communication
        
        This method sends a shutdown message to Unity and waits for acknowledgment
        before closing the connection.
        """
        try:
            print("[Python] Sending shutdown request to Unity...")
            shutdown_data = {
                "message_type": "shutdown"
            }
            
            # Set a timeout for the shutdown response
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            try:
                self.socket.send_string(json.dumps(shutdown_data))
                response_str = self.socket.recv_string()
                response = json.loads(response_str)
                
                if response.get('status') == 'success':
                    print("[Python] Unity acknowledged shutdown request")
                else:
                    print(f"[Python] Unity shutdown response: {response}")
                    
            except zmq.Again:
                print("[Python] Unity shutdown response timeout")
            except Exception as e:
                print(f"[Python] Error during Unity shutdown: {e}")
                
        except Exception as e:
            print(f"[Python] Failed to send shutdown request: {e}")
        finally:
            # Clear the timeout setting
            self.socket.setsockopt(zmq.RCVTIMEO, -1)
            
    def end_process(self):
        """Clean up resources and close connections"""
        try:
            self.socket.close()
            self.context.term()
            print("[Python] Unity communication resources cleaned up")
        except Exception as e:
            print(f"[Python] Error during cleanup: {e}")
        
        
        