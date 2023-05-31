# %%
import logging
from distutils.util import strtobool
from re import T
from time import sleep

# Importing models and REST client class from Community Edition version
from tb_rest_client.rest_client_ce import *

# Importing the API exception
from tb_rest_client.rest import ApiException
from utci import universal_thermal_climate_index as UTCI
import json


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

# %%
# Creating the REST client object with context manager to get auto token refresh

with RestClientCE(base_url=url) as rest_client:
    try:
        rest_client.login(username=username, password=password)
    except ApiException as e:
        logging.exception(e)
# %%


# %%


def telemetry_refresh():
    global Rh, globe_temp, air_vel, air_temp, pressure, time_stamp, mode_flag, fan_state, mist_state, roof_state
    with RestClientCE(base_url=url) as rest_client:
        try:
            rest_client.login(username=username, password=password)
            res = rest_client.get_latest_timeseries("DEVICE", ESP_id)
            logging.info("Device info:\n%r", res)
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


#%%
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
    RPC_fan["params"] = peri_state[0]
    RPC_roof["params"] = peri_state[1]
    RPC_mist["params"] = peri_state[2]
    with RestClientCE(base_url=url) as rest_client:
        try:
            rest_client.login(username=username, password=password)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_fan)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_roof)
            rest_client.handle_two_way_device_rpc_request(ESP_id,RPC_mist)
        except ApiException as e:
            logging.exception(e)


# %%
delta_v_fan = [0, 3.5, 4.2, 4.7]
delta_gt_roof = [0, -1]
delta_t_mist = [0, -1]
delta_Rh_mist = [0, 5]

UTCI_list = [0] * 16
T_list = [0] * 16
GT_list = [0] * 16
RH_list = [0] * 16
V_list = [0] * 16
P_list = [0] * 16

peri_state = [
    [0, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
    [0, 1, 1],
    [1, 0, 0],
    [1, 0, 1],
    [1, 1, 0],
    [1, 1, 1],
    [2, 0, 0],
    [2, 0, 1],
    [2, 1, 0],
    [2, 1, 1],
    [3, 0, 0],
    [3, 0, 1],
    [3, 1, 0],
    [3, 1, 1],
]

# %%
def UTCI_find(in_list,threshold):
    x = in_list + [threshold]
    x = sorted(range(len(x)), key=x.__getitem__)
    for i in range(0, len(x)):
        if x[i] == len(in_list):
            if i == 0:
                return [x[j + 1]]
            else:
                return [x[j] for j in range(0, len(x)) if j < i]
def power(peri_state):
    power_fan = [0, 3, 4, 5]
    power = power_fan[peri_state[0]] + 6 * peri_state[1] + 4 * peri_state[2]
    return power
for i in range(0, 16):
    P_list[i] = power(peri_state[i])

#%%
while 1:
    telemetry_refresh()
    while(mode_flag):
        for j in range(0, 16):
            V_list[j] = air_vel + delta_v_fan[peri_state[j][0]] - delta_v_fan[fan_state]
            if V_list[j] < 0:
                    V_list[j] = 0
            GT_list[j] = (
                    globe_temp + delta_gt_roof[peri_state[j][1]] - delta_gt_roof[roof_state]
                )
            RH_list[j] = Rh + delta_Rh_mist[peri_state[j][2]] - delta_Rh_mist[mist_state]
            if RH_list[j] < 0:
                    RH_list[j] = 0
            if RH_list[j] > 100:
                    RH_list[j] = 100
            T_list[j] = air_temp + delta_t_mist[peri_state[j][2]] - delta_t_mist[mist_state]
            UTCI_list[j] = UTCI(T_list[j], GT_list[j], RH_list[j], V_list[j])
        ibuff = -1
        x = 100
        for i in UTCI_find(UTCI_list,26):
            if P_list[i] < x:
                x = P_list[i]
                ibuff = i
        if ibuff==0 and min(UTCI_list)>26:
            ibuff=15
        print(peri_state[ibuff])
        print(UTCI_list)
        RPC_update(peri_state[ibuff])
        for i in range(0,60):
            sleep(1)
            #print(".")
        telemetry_refresh()


#%%
with RestClientCE(base_url=url) as rest_client:
    try:
        rest_client.login(username=username, password=password)
    except ApiException as e:
        logging.exception(e)
#%%
tejson={}
tejson1=[]
#%%
t1=1648861200000
#%%
while t1<1648868400000:
    tejson.update(rest_client.get_timeseries("DEVICE", ESP_id,"UTCI",t1,t1+3600000,limit=1000))
    t1=t1+3600000
    tejson1+=tejson['UTCI']
#%%
file = open('filename1.json', 'w')

file.write(json.dumps(tejson1))

file.close()

#%%
import pandas as pd
df = pd.read_json (r'filename1.json')
df.to_csv (r'filename1.csv', index = None)
#%%
# while(1):
#     telemetry_refresh()
#     org = UTCI(air_temp, globe_temp, Rh, air_vel)
#     while(mode_flag):


#         if org > 26:
#             UTCI_fan = [0,0,0,0]
#             UTCI_mist = [0, 0]
#             UTCI_roof = [0, 0]
#             fan_buff = RPC_fan["params"]
#             mist_buff = RPC_roof["params"]
#             roof_buff = RPC_mist["params"]
#             for i in range(0, len(UTCI_fan)):
#                 UTCI_fan[i] = UTCI(
#                     air_temp,
#                     globe_temp,
#                     Rh,
#                     air_vel + delta_v_fan[i] - delta_v_fan[RPC_fan["params"]],
#                 )
#             fan_buff = fan_find(UTCI_fan)

#             if UTCI_fan[fan_buff] > 26:
#                 for i in range(0, 2):
#                     UTCI_mist[i] = UTCI(
#                         air_temp + delta_t_mist[i] - delta_t_mist[RPC_mist["params"]],
#                         globe_temp,
#                         Rh + delta_Rh_mist[i] - delta_Rh_mist[RPC_mist["params"]],
#                         air_vel + delta_v_fan[fan_buff] - delta_v_fan[RPC_fan["params"]],
#                     )
#                 if UTCI_mist[0] < UTCI_mist[1]:
#                     mist_buff = 0
#                 else:
#                     mist_buff = 1
#             if UTCI_mist[mist_buff] > 26:
#                 for i in range(0, 2):
#                     UTCI_roof[i] = UTCI(
#                         air_temp + delta_t_mist[mist_buff] - delta_t_mist[RPC_mist["params"]],
#                         globe_temp + delta_gt_roof[i] - delta_gt_roof[RPC_roof["params"]],
#                         Rh + delta_Rh_mist[mist_buff] - delta_Rh_mist[RPC_mist["params"]],
#                         air_vel + delta_v_fan[fan_buff] - delta_v_fan[RPC_fan["params"]],
#                     )
#                 if UTCI_roof[0] < UTCI_roof[1]:
#                     roof_buff = 0
#                 else:
#                     roof_buff = 1
#             RPC_fan["params"] = fan_buff
#             RPC_roof["params"] = mist_buff
#             RPC_mist["params"] = roof_buff
#             RPC_update()
#     sleep(60)
