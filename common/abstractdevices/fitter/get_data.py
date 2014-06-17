
import numpy as np
import pylab as pl
import os

BASEPATH = "/home/cct/LabRAD/cct/data/Experiments.dir"
BASEPATH2 = "/home/cct/LabRAD/cct/data/ScriptScanner."

def Value(x,y):
    return x

def generate_file_list(date, basepath=BASEPATH, add_path=BASEPATH2, experiments=None):
    if experiments == None:
        dirlist = os.listdir(basepath)
        dirlist.remove('Excitation729.dir')   
    else:
        dirlist = experiments
    dirlist += [add_path]
    datedir_list = []
    for dirname in dirlist:
        datedir = BASEPATH +'/'+dirname +'/' + date +'.dir'
        if os.path.isdir(datedir):
            datedir_list.append(datedir)
    add_path = add_path+'/' + date +'.dir'
    if (os.path.isdir(add_path)):
            datedir_list.append(add_path)
    time_dict = {}
    for dirname in datedir_list:
        time_list = os.listdir(dirname)
        for time in time_list:
            key = time.strip('.dir')
            if time_dict.has_key(key):
                print "Warning Key " + str(key) + " already used: " + dirname +'/'+time
                print "Existing entry: " + str(time_dict[key])
            if os.path.splitext(key)[1] == '':
                time_dict[key] = dirname +'/' + time
    return time_dict

def get_parameters(time, time_dict):
    import ConfigParser
    Config = ConfigParser.ConfigParser()
    dirname = time_dict[time]
    dirlist = os.listdir(dirname)
    dirlist.remove("session.ini")
    for fname in dirlist:
 #      print os.path.splitext(fname)[1]

        if os.path.splitext(fname)[1] == '.ini':
#            print "reading " + dirname +'/'+fname
            Config.read(dirname +'/'+fname)
    param_dict ={}
    for sect in Config.sections():
        option_list = Config.options(sect)
        if 'Parameter' in sect:
            dstr = 'data = '+Config.get(sect,'data')
            exec(dstr)
            param_dict[Config.get(sect,'label')] = data
#        for option in option_list:
#            param_dict[option]
        param_dict['Scanned Value'] = Config.get('Independent 1','label') 
    return param_dict


class ReadData():
    def __init__(self, date, time_str=None, experiment=None,  basepath = BASEPATH, get_errors=True):
        self.basepath = basepath
        self.date = date
        self.experiment = experiment
        self.get_errors = get_errors
        if time_str != None:
            self.get_data(time_str, experiment)
    
    def calcerror(self, data, nr_of_cycles=100):
        return np.sqrt(data*(1-data)/nr_of_cycles)
        
    def get_data(self, time_str, experiment=None, basepath=BASEPATH):
        if experiment == None:
            experiment = self.experiment

        pathname = self.basepath+ '/' + experiment + ".dir/" + self.date + '.dir/' + time_str + '.dir/'
        for files in os.listdir(pathname):
            if files.endswith("csv"):
                self.data = np.loadtxt(pathname + files,delimiter=',')
        if self.get_errors == False:
            return self.data
        else:
            a = np.zeros((self.data.shape[0],self.data.shape[1]+1))
            a[:,0:-1] = self.data
            a[:,2] = self.calcerror(a[:,1])
            self.data = a
            return a

