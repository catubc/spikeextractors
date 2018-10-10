import spikeinterface as si

import os, json
import numpy as np
from pynwb import NWBHDF5IO
from datetime import datetime
from pynwb import NWBFile
from pynwb.ecephys import ElectricalSeries

class CopyRecordingExtractor(si.RecordingExtractor):
    def __init__(self, other):
        si.RecordingExtractor.__init__(self)
        self._other=other
        
    def getNumChannels(self):
        return self._other.getNumChannels()
    
    def getNumFrames(self):
        return self._other.getNumFrames()
    
    def getSamplingFrequency(self):
        return self._other.getSamplingFrequency()
        
    def getTraces(self, start_frame=None, end_frame=None, channel_ids=None):
        return self._other.getTraces(start_frame=start_frame,end_frame=end_frame,channel_ids=channel_ids)
    
    def getChannelInfo(self, channel_id):
        return self._other.getChannelInfo(channel_id)

class NwbRecordingExtractor(CopyRecordingExtractor):
    def __init__(self, path, acquisition_name=None):
        self._path=path
        self._acquisition_name=acquisition_name
        with NWBHDF5IO(path, 'r') as io:
            nwbfile = io.read()
            if acquisition_name is None:
                a_names=list(nwbfile.acquisition.keys())
                if len(a_names)>1:
                    raise Exception('More than one acquisition found. You must specify acquisition_name.')
                if len(a_names)==0:
                    raise Exception('No acquisitions found in the .nwb file.')
                acquisition_name=a_names[0]
            ts=nwbfile.acquisition[acquisition_name]
            self._nwb_timeseries=ts
            M=np.array(ts.data).shape[1]
            if M != len(ts.electrodes):
                raise Exception('Number of electrodes does not match the shape of the data {}<>{}'.format(M,len(ts.electrodes)))
            geom=np.zeros((M,3))
            for m in range(M):
                geom[m,:]=[ts.electrodes[m][1],ts.electrodes[m][2],ts.electrodes[m][3]]
            if hasattr(ts,'timestamps') and ts.timestamps:
                samplerate=1/(ts.timestamps[1]-ts.timestamps[0]) # there's probably a better way
            else:
                samplerate=ts.rate*1000
            data=np.copy(np.transpose(ts.data))
            NRX=si.NumpyRecordingExtractor(timeseries=data,samplerate=samplerate,geom=geom)
            CopyRecordingExtractor.__init__(self,NRX)

    @staticmethod
    def writeRecording(recording_extractor,save_path,acquisition_name):
        M=recording_extractor.getNumChannels()
        N=recording_extractor.getNumFrames()
        
        nwbfile = NWBFile(
            source='SpikeInterface::NwbRecordingExtractor',
            session_description='',
            identifier='',
            session_start_time=datetime.now(),
            experimenter='',
            lab='',
            institution='',
            experiment_description='',
            session_id=''
        )
        device = nwbfile.create_device(name='device_name', source="device_source")
        eg_name = 'electrode_group_name'
        eg_source = "electrode_group_source"
        eg_description = "electrode_group_description"
        eg_location = "electrode_group_location"

        electrode_group = nwbfile.create_electrode_group(
            name=eg_name,
            source=eg_source,
            location=eg_location,
            device=device,
            description=eg_description
        )
        
        for m in range(M):
            id=m
            info0=recording_extractor.getChannelInfo(m)
            location=info0['location']
            impedence=-1.0
            while len(location)<3:
                location=np.append(location,[0])
            nwbfile.add_electrode(
                id,
                x=location[0], y=location[1], z=location[2],
                imp=impedence,
                location='electrode_location',
                filtering='none',
                group=electrode_group,
                description='electrode_description'
            )
        electrode_table_region = nwbfile.create_electrode_table_region(
            list(range(M)), 
            'electrode_table_region'
        )

        rate = recording_extractor.getSamplingFrequency()/1000
        ephys_data = recording_extractor.getTraces().T
        
        ephys_ts = ElectricalSeries(
            name=acquisition_name,
            source='acquisition_source',
            data=ephys_data,
            electrodes=electrode_table_region,
            starting_time=recording_extractor.frameToTime(0),
            rate=rate,
            resolution=1e-6,
            comments='Generated from SpikeInterface::NwbRecordingExtractor',
            description='acquisition_description'
        )
        nwbfile.add_acquisition(ephys_ts)
        if os.path.exists(save_path):
            os.remove(save_path)
        with NWBHDF5IO(save_path, 'w') as io:
            io.write(nwbfile)