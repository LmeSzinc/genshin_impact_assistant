import pyautogui
import character,tastic,threading, img_manager as imgM, posi_manager as posiM
from unit import *
from timer_module import Timer
from interaction_background import Interaction_BGD
from base_threading import Base_Threading

class Switch_Character_Operator(Base_Threading):
    def __init__(self, chara_list):
        super().__init__()
        self.chara_list = chara_list
    
    def run(self):
        while(1):
            if self.stop_threading_flag:
                return 0
            
            if self.pause_threading_flag:
                time.sleep(1)
                continue
            
            
    
