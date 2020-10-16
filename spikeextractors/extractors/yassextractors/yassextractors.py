import yaml
import numpy as np
from pathlib import Path

from spikeextractors import SortingExtractor
from spikeextractors.extractors.numpyextractors import NumpyRecordingExtractor
from spikeextractors.extraction_tools import check_valid_unit_id


class YassSortingExtractor(SortingExtractor):

    extractor_name = 'YassExtractor'
    mode = 'folder'
    installed = True  # check at class level if installed or not

    has_default_locations = False
    is_writable = False
    installation_mesg = "YASS NOT INSTALLED"  # error message when not installed
    
    
    def __init__(self, root_dir):
        SortingExtractor.__init__(self)

        ## All file specific initialization code can go here.
        # If your format stores the sampling frequency, you can overweite the self._sampling_frequency. This way,
        # the base method self.get_sampling_frequency() will return the correct sampling frequency
        
        self.root_dir = root_dir
        r = Path(self.root_dir)

        self.fname_spike_train = r / 'tmp' / 'output' / 'spike_train.npy'
        self.fname_templates = r /'tmp' / 'output' / 'templates' / 'templates_0sec.npy'
        self.fname_config = r / 'config.yaml'
        
        
        # set defaults to None so they are only loaded if user requires them
        
        self.spike_train = None
        self.temps = None

        # Read CONFIG File
        with open(self.fname_config, 'r') as stream:
            self.config = yaml.safe_load(stream)
        
        #self._sampling_frequency = my_sampling_frequency

    def get_unit_ids(self):

        if self.spike_train is None:
            self.spike_train = np.load(self.fname_spike_train)
        
        unit_ids = np.unique(self.spike_train[:,1])
        
        return unit_ids
    
    def get_temps(self):

        # Electrical images/templates.
        
        if self.temps is None:
            self.temps = np.load(self.fname_templates)
                    
        return self.temps

    def get_unit_spike_train(self, unit_id, start_frame=None, end_frame=None):

        '''Code to extract spike frames from the specified unit.
        '''

        if self.spike_train is None:
            self.spike_train = np.load(self.fname_spike_train)
            
        # find unit id spike times
        idx = np.where(self.spike_train[:,1]==unit_id)
        spike_times = self.spike_train[idx,0].squeeze()

        # find spike times
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = 1E50 # use large time
            
        idx2 = np.where(np.logical_and(spike_times>=start_frame, spike_times<end_frame))[0]
        spike_times = spike_times[idx2]
        
        return spike_times
    
    
    def get_sampling_frequency(self):

        return self.config['recordings']['sampling_rate']
    
    #@staticmethod
    #def write_sorting(sorting, save_path):
    #    '''
    #    This is an example of a function that is not abstract so it is optional if you want to override it. It allows other
    #    SortingExtractors to use your new SortingExtractor to convert their sorted data into your
    #    sorting file format.
    #    '''