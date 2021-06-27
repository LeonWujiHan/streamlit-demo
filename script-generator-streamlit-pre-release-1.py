import time
import re
import os
import datetime
import numpy as np
import pandas as pd
import streamlit as st
from scipy.io import loadmat

st.title('Script Generator for FISH PKU')
'Version beta, June 13th 2021'
'By Leon Han'


def index_to_bit_pos(_max, _pos):
    return str(bin(2**(_max-_pos)))[2:].zfill(_max)


with st.beta_expander('Device and Configurations'):
    'Modify the textbox and press enter to re-assign the values.'
    '**Current working config: **'
    base_directory = st.text_input(
        'Base directory', r'C:\Users\Dell\Documents\FISH_images')
    selector = st.text_input('Selector', 'VICI_EMHCA[0]')
    pump = st.text_input('Pump', 'SP_CENTRIS')
    temp_controller = st.text_input('Temperature controller', 'TC_720')
    bypass_rate = st.slider('Bypass rate', 0, 20, 5)
    fluid_interval = st.slider('Fluid interval', 0, 5, 2)
    unassigned_name = st.text_input('Unassigned valve name', 'next_valve')
    light_source = st.text_input('Light source', 'XT600')
    light_filter = st.text_input('Light filter', 'ASI')
    capture_handle = st.text_input('Capture handle', 'CAM_PROSCAN_WDI_AF')
    capture_zscan_handle = st.text_input(
        'Capture handle (z scan)', 'CAM_PROSCAN_WDI_AF_ZSCAN')
    scan_info = st.text_input('Scan info file', 'ASI_20xscan.txt')
    tile_info = st.text_input('Tile info file', 'TileInfo.mat')
    base_name = st.text_input('Base name', 'base')

with st.beta_expander('Experiment Info', True):
    'Create or specify experiment directory here.'
    experiment_name = st.text_input('Experiment name', 'generator_test')
    date = st.date_input('Experiment date', datetime.date.today())
    date_f = date.strftime('%Y%m%d')
    script_directory = os.path.join(
        base_directory, f'{date_f}_{experiment_name}')
    if st.button('Create'):
        try:
            os.mkdir(script_directory)
            st.write(f'Successfully created `{script_directory}`.')
        except FileExistsError:
            st.write(f'`{script_directory}` already exists.')
    tile_mat_directory = os.path.join(script_directory, tile_info)
    if os.path.isfile(tile_mat_directory):
        tile_mat = loadmat(tile_mat_directory)
        tile_x, tile_y = tile_mat['TileX'][0][0], tile_mat['TileY'][0][0]
        tile_num = tile_x * tile_y

with st.beta_expander('Reagent-valve Assignments'):
    'Upload formatted reagents spreadsheet here. If no file is specified, default file `default_reagents.csv` will be used.'
    reagents_file = st.file_uploader('Reagents table', type='csv')
    reagents_custom_file = os.path.join(
        script_directory, f'custom_reagents_{date_f}.csv')
    if reagents_file is not None:
        reagents_table = pd.read_csv(reagents_file)
        if os.path.isdir(script_directory):
            reagents_table.to_csv(reagents_custom_file, index=False)
    elif os.path.isfile(reagents_custom_file):
        reagents_table = pd.read_csv(reagents_custom_file)
        st.write(f'Loaded `{reagents_custom_file}`.')
    else:
        reagents_table = pd.read_csv('./default_reagents.csv')
        if os.path.isdir(script_directory):
            reagents_table.to_csv(reagents_custom_file, index=False)
    valve_index = st.slider('Valve index', 1, 14, 9)
    reagent_name = st.text_input('Reagent', 'TCEP')
    reagent_description = st.text_input(
        'Reagent description', 'tris(2-carboxyethyl)phosphine')
    '**Preview**'
    reagents_holder = st.empty()
    if st.button('Update', key='update reagent'):
        if reagents_table['Valve'].isin([valve_index]).any():
            reagents_table.loc[reagents_table['Valve']
                               == valve_index, 'Reagent'] = reagent_name
            reagents_table.loc[reagents_table['Valve'] ==
                               valve_index, 'Description'] = reagent_description
        else:
            reagent_temp = pd.DataFrame([[valve_index, reagent_name, reagent_description]], columns=[
                                        'Valve', 'Reagent', 'Description'])
            reagents_table = reagents_table.append(
                reagent_temp, ignore_index=True)
        if os.path.isdir(script_directory):
            reagents_table.to_csv(reagents_custom_file, index=False)
        st.write('Reagent updated.')
        reagents_table_show = reagents_table.set_index('Reagent')
        reagents_holder.dataframe(reagents_table_show)
    reagents_table_show = reagents_table.set_index('Reagent')
    reagents_holder.dataframe(reagents_table_show)

with st.beta_expander('Optics Configurations'):
    st.write('Upload configurations for light source and camera. If no file is specified, choose from the profiles below:')
    sample_optics_type = st.selectbox('Default profiles', ('Tissue', 'Beads'))
    optics_file = st.file_uploader('Optics configurations', type='csv')
    if optics_file is not None:
        optics_table = pd.read_csv(optics_file)
    else:
        optics_table = pd.read_csv(
            f'./default_optics_config_{sample_optics_type.lower()}.csv')
    optics_table = optics_table.set_index('Channel Name')
    '**Preview**'
    optics_holder = st.empty()
    optics_holder.dataframe(optics_table)
    capture_channels = st.multiselect(
        'Channels for capture', list(optics_table.index), ['Cy3', 'Cy5'])
    zscan_step = st.slider('Z scan step', 1, 5, 2)
    zscan_depth = st.slider('Z scan depth', zscan_step,
                            10*zscan_step, 4*zscan_step, zscan_step)
    zscan_enable = st.checkbox('Enable Z scan by default', False)


class CommandLists:

    def __init__(self, _file_name=''):
        if _file_name == '':
            _file_name = file_name
        self.file_name = _file_name
        self.script_directory = script_directory
        self.operations = []
        self.time_consumption = 0
        self.reagents = reagents_table_show
        self.pump = pump
        self.selector = selector
        self.temp_controller = temp_controller
        self.bypass_rate = bypass_rate
        self.unassigned_name = unassigned_name
        self.fluid_interval = fluid_interval
        self.light_filter = light_filter
        self.capture_handle = capture_handle
        self.capture_zscan_handle = capture_zscan_handle
        self.z_depth = zscan_depth
        self.z_step = zscan_step
        self.z_enable = zscan_enable
        self.scan_info = scan_info
        self.channels = optics_table
        self.capture_channels = capture_channels
        self.light_source = light_source
        self.base_name = base_name

    def annotate(self, text):
        self.operations.append('// '+text)

    def exposure(self, c, e):
        self.channels.loc[c, 'Exposure'] = e

    def exposure_format(self, c, zscan=None):
        channels_bit = index_to_bit_pos(
            6, self.channels.loc[c, 'Channel Index'])
        if not zscan:
            return f"{{{c.lower()},{self.channels.loc[c,'Exposure']},{channels_bit}}}"
        else:
            return f"{{{c.lower()},{self.channels.loc[c,'Exposure']},{channels_bit},{self.z_depth},{self.z_step}}}"

    def light_high_speed(self):
        self.operations.append(f'{self.light_source} HSEN')

    def light_high_speed_off(self):
        self.operations.append(f'{self.light_source} HSDS')

    def intensity(self, v, *args, output=True):
        for c in args:
            if c in self.channels.index:
                self.channels.loc[c, 'Intensity'] = v
        if output:
            out = 0
            for c in args:
                out += 2**(6-self.channels[c][0])
            outstr = str(bin(out))[2:].zfill(6)
            self.light_high_speed()
            self.operations.append(
                f'{self.light_source} INTENSITY {v},{outstr}')
            self.light_high_speed_off()

    def bypass(self):
        self.operations.append('SV[1] 1')
        self.operations.append('SV[0] 1')

    def switch_to_chip(self):
        self.operations.append('SV[1] 0')
        self.operations.append('SV[0] 0')

    def wait(self, nwait):
        self.operations.append('WAIT '+str(nwait))
        self.time_consumption += nwait

    def pump_pull(self, rate, volume):
        self.operations.append(f'{self.pump} PULL {rate},{volume}')
        self.time_consumption += (volume/rate)

    def pump_push(self, rate, volume):
        self.operations.append(f'{self.pump} PULL {rate},{volume}')
        self.time_consumption += (volume/rate)

    def pump_zero(self):
        self.operations.append(f'{self.pump} ZERO_PLUNGER')

    def switch_valve(self, desc):
        if desc in self.reagents.index:
            self.operations.append(
                f"{self.selector} P {self.reagents.loc[desc,'Valve']}")
        else:
            self.operations.append(f'{self.selector} P {desc}')

    def temp(self, t):
        self.operations.append(f'{self.temp_controller} SET 1,{t}')
        self.operations.append(f'{self.temp_controller} WAIT')

    def temp_off(self):
        self.operations.append(f'{self.temp_controller} SET 0,25')

    def single_fluid(self, reagent, rate, volume, annotation=''):
        self.annotate(f'{reagent} {rate}uL/s total {volume}uL')
        if annotation != '':
            self.annotate(annotation)
        self.switch_valve(reagent)

        if f'{self.selector} P {self.unassigned_name}' not in self.operations:
            self.bypass()
            self.pump_pull(self.bypass_rate, 60)
            self.wait(2)
            self.switch_to_chip()
        elif reagent in ['USB', 'PBS']:
            self.bypass()
            self.pump_pull(80, 150)
            self.wait(2)
            self.switch_to_chip()
        else:
            #  self.pump_pull(bypass_rate,10)
            self.wait(1)

        self.pump_pull(rate, volume-50)
        self.wait(2)
        self.switch_valve('AIR')
        self.pump_pull(rate, self.fluid_interval)
        self.wait(2)
        self.switch_valve(self.unassigned_name)
        self.pump_pull(rate, 50-self.fluid_interval)
        self.wait(2)

    def switch_filter(self, n):
        self.operations.append(f'{self.light_filter} FILTER {n}')

    def capture(self, i, *args):  # must have same filter
        if type(args[-1]) == bool:
            _zscan = args[-1]
            channels = [arg for arg in args if type(arg) != bool]
        else:
            _zscan = self.z_enable
            channels = args
        self.light_high_speed()
        f = False
        s = f'{(self.capture_zscan_handle if _zscan else self.capture_handle)} {i},{self.base_name},[{self.scan_info}]'
        for c in channels:
            if not f:
                self.switch_filter(self.channels.loc[c, 'Filter'])
                f = True
            s += f',{self.exposure_format(c, _zscan)}'
        self.operations.append(s)
        if _zscan:
            self.time_consumption += 0
        self.light_high_speed_off()

    def single_capture(self, i, _zscan=None):
        if not _zscan:
            _zscan = self.z_enable
        self.capture(i, *self.capture_channels, _zscan)

    def domino(self):
        unassigned = f'{selector} P {self.unassigned_name}'
        while unassigned in self.operations:
            i = self.operations.index(unassigned)
            if unassigned not in self.operations[i+1:len(self.operations)]:
                self.operations[i] = f'{selector} P AIR'
            else:
                for j in range(i+1, len(self.operations)):
                    if f'{selector} P' in self.operations[j]:
                        tmp = self.operations[j]
                        self.operations[i] = tmp
                        break

    def print_command(self):
        self.domino()
        print('\n'.join(self.operations))

    def retrieve_command(self):
        self.domino()
        return self.operations

    def save_command(self):
        self.domino()
        s = '\n'.join(self.operations)
        time_stamp = time.strftime('%y%m%d_%H%M')
        output_name = f'{time_stamp}_{self.file_name}.txt'
        output = open(os.path.join(self.script_directory, output_name), 'w')
        output.write(s)
        output.close()
        st.write(f'Saved as `{output_name}`.')

    def show_summary(self):
        st.write('Reagents')
        st.dataframe(self.reagents)
        st.write('Optics')
        st.dataframe(self.channels)

#  chemistry definitions
    def incorporate(self, _rate=5, _volume_low=70, _volume_high=200, SDS_wash=True):
        self.temp(60)
        self.wait(10)
        self.single_fluid('ICM', _rate, _volume_low)
        self.wait(120)
        if SDS_wash:
            self.single_fluid('USB', _rate, _volume_high)
            self.single_fluid('SDS', _rate, 500)
        self.single_fluid('USB', _rate, 300)
        self.temp(20)
        self.wait(15)
        self.single_fluid('USM', _rate, _volume_low)
        self.wait(10)

    def cleave(self, _rate=10, cool=True, _volume_low=70, _volume_high=200):
        self.temp(60)
        self.single_fluid('USB', _rate, _volume_high)
        self.wait(10)
        self.single_fluid('CRM', _rate, _volume_low)
        self.wait(400)
        self.single_fluid('CWM', _rate, _volume_high)
        if cool:
            self.temp(20)
            self.wait(10)
            self.single_fluid('Eth07', 30, 150)
        self.single_fluid('USB', _rate, 300)

    def complete_cycle(self):
        self.cleave(cool=False)
        self.incorporate()


with open('./script_snippets.txt') as f:
    raw_list = f.read().split('>>')
    raw_list = [s.strip('\n').strip().split('\n') for s in raw_list if s != '']
    snippets = {x[0]: x[1:] for x in raw_list}


def format_command(c, prefix):
    if c.startswith('>'):
        return c.strip('>').strip()
    else:
        if re.match(r'(\s+)\w', c):
            return re.sub(r'(\s+)(\w)', r'\1'+prefix+r'.\2', c)
        else:
            return f'{prefix}.{c}'


snippets_str = {}
for key in snippets:
    snippets_str[key] = '\n'.join(
        [format_command(s, 'l') for s in snippets[key]])


def highlight_note(s):
    is_note = s.apply(lambda x: x.startswith('//'))
    return ['background-color: lightgray' if v else '' for v in is_note]


with st.beta_expander('Script Edit', True):
    file_name = st.text_input('File name', 'seq')
    tile_mat_directory = os.path.join(script_directory, tile_info)
    if os.path.isfile(tile_mat_directory):
        tile_mat = loadmat(tile_mat_directory)
        tile_x, tile_y = tile_mat['TileX'][0][0], tile_mat['TileY'][0][0]
        tile_num = tile_x * tile_y
    l = CommandLists()
    script_commands_height = st.slider('Height', 100, 1000, 300, 100)
    script_commands = st.text_area(
        'Commands', '', height=script_commands_height)
    preview_holder = st.empty()
    if st.button('Generate'):
        exec(script_commands)
        preview_holder.dataframe(pd.DataFrame(
            {'Commands': l.retrieve_command()}).style.apply(highlight_note))
    if st.button('Save'):
        if not os.path.isdir(script_directory):
            os.makedirs(script_directory)
        exec(script_commands)
        l.save_command()
        l.show_summary()

with st.beta_expander('Snippets', True):
    temp_lst_prefix = 'l_temp'
    snippets_select = st.selectbox('Select snippets', [*snippets_str.keys()])
    st.markdown(f"```python\n{snippets_str[snippets_select]}\n```")
    if st.button('Save', key='save_snippet'):
        temp_command = f"{temp_lst_prefix} = CommandLists(\'{snippets_select.replace(' ','_').lower()}\')\n"
        temp_command += '\n'.join([format_command(s, temp_lst_prefix)
                                   for s in snippets[snippets_select]])
        temp_command += f'\n{temp_lst_prefix}.save_command()'
        exec(temp_command)
        # st.markdown(f'```python\n{temp_command}\n```')
