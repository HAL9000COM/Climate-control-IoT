# %%
from __future__ import absolute_import, division, print_function
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3 import PPO
from utci import universal_thermal_climate_index as UTCI
from time import sleep
from datetime import datetime
from gym import spaces
import gym
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import logging
import IPython
from distutils.util import strtobool

# from tf_agents.trajectories import time_step as ts

from tensorflow.keras import layers

# from gym_env import ESPEnv
# Importing models and REST client class from Community Edition version
from tb_rest_client.rest_client_ce import *

# Importing the API exception
from tb_rest_client.rest import ApiException

# %%
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - %(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# %%
# ThingsBoard REST API URL
url = "https://example.com"
# Default Tenant Administrator credentials
username = "tenant@example.com"
password = "password"
ESP_id = 'deadbeef-ffff-ffff-ffff-ffffffffffff'


def telemetry_refresh():
    global Rh, globe_temp, air_vel, air_temp, pressure, time_stamp, mode_flag, fan_state, mist_state, roof_state
    with RestClientCE(base_url=url) as rest_client:
        try:
            rest_client.login(username=username, password=password)
            res = rest_client.get_latest_timeseries("DEVICE", ESP_id)
            #logging.info("Device info:\n%r", res)
        except ApiException as e:
            logging.exception(e)
    Rh = float(res["RH"][0]["value"])
    globe_temp = float(res["globe_temp"][0]["value"])
    air_vel = float(res["air_vel"][0]["value"])
    air_temp = float(res["air_temp"][0]["value"])
    pressure = float(res["pressure"][0]["value"])
    mode_flag = strtobool(res["mode"][0]["value"])
    fan_state = int(res["fan"][0]["value"])
    roof_state = strtobool(res["roof"][0]["value"])
    mist_state = strtobool(res["mist"][0]["value"])
    time_stamp = res["air_temp"][0]["ts"]


telemetry_refresh()
# %%
RPC_fan = {"method": "setFan", "params": 0}
RPC_roof = {"method": "setRoof", "params": 0}
RPC_mist = {"method": "setMist", "params": 0}
RPC_fan["params"] = 0
RPC_roof["params"] = 0
RPC_mist["params"] = 0

# %%
def RPC_update(peri_state):
    RPC_fan["params"] = int(peri_state[0])
    RPC_roof["params"] =int( peri_state[1])
    RPC_mist["params"] = int(peri_state[2])
    with RestClientCE(base_url=url) as rest_client:
        try:
            rest_client.login(username=username, password=password)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_fan)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_roof)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_mist)
        except ApiException as e:
            logging.exception(e)

class ESPEnv(gym.Env):
    """
    Observation:
        Type: Box(7)
        Num     Observation               Min                     Max
        0       air_temp                  -Inf                    Inf
        1       air_vel                   0                       Inf
        2       globe_temp                -Inf                    Inf
        3       pressure                  0                       Inf
        4       Rh                        0                       100
    Actions:
        Type: MultiDiscrete([ 4, 2, 2 ])
        Num   Action
        0     Fan 0 1 2 3
        1     Mist
        2     roof
    """

    def __init__(self):
        observation_low = np.array(
            [np.finfo(np.float32).min, 0.0, np.finfo(np.float32).min, 0.0, 0.0]
        )
        observation_high = np.array(
            [
                np.finfo(np.float32).max,
                np.finfo(np.float32).max,
                np.finfo(np.float32).max,
                np.finfo(np.float32).max,
                100.0,
            ]
        )
        self.observation_space = spaces.Box(
            observation_low, observation_high, dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([4, 2, 2])
        telemetry_refresh()
        global time_stamp_buff
        time_stamp_buff = time_stamp
        reward = 26 - UTCI(air_temp, globe_temp, Rh, air_vel)
        self.state = (
            air_temp,
            air_vel,
            globe_temp,
            pressure,
            Rh,
        )
        self.steps_beyond_done = None

    def reset(self):
        telemetry_refresh()
        global time_stamp_buff
        time_stamp_buff = time_stamp
        return self._next_observation()

    def _next_observation(self):
        global time_stamp_buff
        time_stamp_local = time_stamp
        while time_stamp_local == time_stamp:
            telemetry_refresh()
            sleep(0.5)
        self.state = (
            air_temp,
            air_vel,
            globe_temp,
            pressure,
            Rh,
        )
        return np.array(self.state, dtype=np.float32)

    def step(self, action):
        RPC_update(action)
        obs = self._next_observation()
        reward = -abs(26 - UTCI(air_temp, globe_temp, Rh, air_vel))
        if time_stamp - time_stamp_buff >= 60000:
            done = True
        else:
            done = False
        return obs, reward, done, {}


# %%
# env = ESPEnv()
# num_states = env.observation_space.shape[0]
# print("Size of State Space ->  {}".format(num_states))
# num_actions = env.action_space.shape[0]
# print("Size of Action Space ->  {}".format(num_actions))

# upper_bound = env.action_space.high[0]
# lower_bound = env.action_space.low[0]

# print("Max Value of Action ->  {}".format(upper_bound))
# print("Min Value of Action ->  {}".format(lower_bound))

# %%

# check_env(ESPEnv())
# %%
# Parallel environments
# env = make_vec_env(env)
env = ESPEnv()
model = PPO("MlpPolicy", env, verbose=2,n_steps=24, batch_size=4,learning_rate=0.01)

#model = PPO.load("PPO_25", env=env)
#%%
model.learn(total_timesteps=720)
model.save("PPO")
# del model  # remove to demonstrate saving and loading
#model = PPO.load("PPO_25")
# %%
obs = env.reset()
while True:
    action, _states = model.predict(obs)
    obs, rewards, dones, info = env.step(action)
    print(obs)
    print(rewards)
    print(action)
# %%
int(action[1])
# %%
RPC_fan["params"]

# %%
RPC_update()
# %%
RPC_fan["params"] = 0
RPC_roof["params"] = 0
RPC_mist["params"] = 0
# %%
