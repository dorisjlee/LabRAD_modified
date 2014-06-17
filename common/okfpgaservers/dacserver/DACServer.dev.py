'''
### BEGIN NODE INFO
[info]
name = DAC Server dev
version = 1.0
description =
instancename = DAC Server dev

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20

### END NODE INFO
'''
import matplotlib.pyplot as plt

import sys
import os
from labrad.server import LabradServer, setting, Signal, inlineCallbacks
from twisted.internet.defer import returnValue
from scipy import interpolate
from scipy.interpolate import UnivariateSpline as UniSpline
from numpy import genfromtxt, arange
import numpy as np
from api import api
from DacConfiguration import hardwareConfiguration as hc
from cct.scripts.experiments.shuttling.shuttle_to import shuttle

SERVERNAME = 'DAC Server dev'
SIGNALID = 270837


class Voltage( object ):
    def __init__( self, channel, analog_voltage = None, digital_voltage = None ):
        self.channel = channel
        self.digital_voltage = digital_voltage
        self.analog_voltage = analog_voltage

    def program( self, set_num ):
        '''
        Compute the hex code to progam this voltage
        '''
        self.set_num = set_num
        if self.analog_voltage is not None:
            (vMin, vMax) = self.channel.allowedVoltageRange
            if self.analog_voltage < vMin: self.analog_voltage = vMin
            if self.analog_voltage > vMax: self.analog_voltage = vMax
            self.digital_voltage = self.channel.computeDigitalVoltage(self.analog_voltage)
        self.hex_rep = self.__getHexRep()
        
    def __getHexRep( self ):
        port = bin(self.channel.dacChannelNumber)[2:].zfill(5)
        if hc.pulseTriggered: setN = bin(self.set_num)[2:].zfill(10)
        else: setN = bin(1)[2:].zfill(10)
        voltage = bin(self.digital_voltage)[2:].zfill(16)
        big = voltage + port + setN + '0'        
        return chr(int(big[8:16], 2)) + chr(int(big[:8],2))+ chr(int(big[24:32], 2)) + chr(int(big[16:24], 2))


class Control(object):
    def __init__(self, name):
        self.name = name
        self.voltage_matrix = {}
        if name == 'none_specified': self.setDefault()
        else: self.readCfile()

    def readCfile(self):
        head = []
        body = []
        if sys.platform.startswith('linux'): Cfile_path = 'Cfiles/' + self.name
        elif sys.platform.startswith('win'): Cfile_path = 'Cfiles\\' + self.name
        Cfile_text = open(Cfile_path).read().split('\n')[:-1]
        for i in range(len(Cfile_text)):
            if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
            else: body.append(Cfile_text[i].split())
        try: self.multipoles = head[0].split('multipoles:')[1].replace(' ','').split(',')
        except: self.multipoles = hc.default_multipoles
        try: self.load_at = self.position = int(head[1].split('load_at:')[1])
        except: self.load_at = self.position = 0
        try: self.move_to = int(head[2].split('move_to:')[1])
        except: self.move_to = 0
        self.num_columns = len(body[0])
        self.multipole_matrix = {elec: {mult: [float(body[eindex + mindex*len(hc.elec_dict)][i]) for i in range(self.num_columns)] 
                                for mindex, mult in enumerate(self.multipoles)} 
                                for eindex, elec in enumerate(sorted(hc.elec_dict.keys()))}        

    def populateVoltageMatrix(self, multipole_vector):
        self.multipole_vector = {m: v for (m,v) in multipole_vector}
        for e in hc.elec_dict.keys():
            self.voltage_matrix[e] = [0. for n in range(self.num_columns)]
            for n in range(self.num_columns):
                for m in self.multipoles: 
                    self.voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * self.multipole_vector[m]
        if self.num_columns > 1: self.interpolateVoltageMatrix()
     
    def interpolateVoltageMatrix(self):
        # fix step size here
        num_positions = 10*(self.num_columns - 1.)
        inc = (self.num_columns-1)/num_positions
        partition = arange(0, (num_positions + 1) * inc, inc)
        splineFit = {elec: UniSpline(range(self.num_columns) , self.voltage_matrix[elec], s=0) for elec in hc.elec_dict.keys()}
        self.voltage_matrix = {elec: splineFit[elec](partition) for elec in hc.elec_dict.keys()}

    def getVoltages(self): 
        return [(e, self.voltage_matrix[e][self.position]) for e in hc.elec_dict.keys()]

    def getLoadVoltages(self):
        return [(e, self.voltage_matrix[e][self.load_at]) for e in hc.elec_dict.keys()]

    def getShuttleVoltagesArb(self, new_position, step_size, duration, loop, loop_delay, overshoot):
        old_position = self.position
        step_size = int(step_size)
        if not loop: self.position = new_position
        N = int(abs(new_position - old_position)/step_size)
        # print N
        if N == 0: self.times = []
        elif N ==1: self.times = [duration*0.]
        else: 
            self.times = [2*duration/np.pi*np.arcsin(np.sqrt(n/(N-1.))) for n in range(N)]
            if loop: self.times += [loop_delay + 2*duration/np.pi*(.5*np.pi + np.arcsin(np.sqrt(n/(N-1.)))) for n in range(N)]            

        if N == 0: 
            position_indicies = []
        elif new_position > old_position:
            new_position -= (new_position - old_position)%step_size
            position_indicies = range( old_position + step_size, new_position + step_size, step_size) 
            if loop: position_indicies += range( old_position, new_position, step_size)[::-1]
        else:
            new_position += (new_position - old_position)%step_size
            position_indicies = range( new_position, old_position, step_size)[::-1]
            if loop: position_indicies += range( new_position + step_size, old_position + step_size, step_size)
        
        if overshoot:
            position_indicies.insert(N, position_indicies[N-1])
            self.times = [2*duration/np.pi*np.arcsin(np.sqrt(n/float(N))) for n in range(N+1)]
            if loop: 
                self.times += [loop_delay + 2*duration/np.pi*(.5*np.pi + np.arcsin(np.sqrt(n/float(N)))) for n in range(N+1)]
                position_indicies.insert(2*N, position_indicies[2*N])
            exp = [np.e**((self.times[i] - self.times[i+1])/hc.filter_RC) for i in range(len(self.times)-1)] + [0.]
            self.voltage_sets = [[(e, (self.voltage_matrix[e][position_indicies[i]] - self.voltage_matrix[e][([old_position] + position_indicies)[i]]*exp[i])/(1.-exp[i])) 
                                for e in hc.elec_dict.keys()] 
                                for i in range(len(position_indicies))]
            nov = [[(e, self.voltage_matrix[e][n]) for e in hc.elec_dict.keys()] for n in position_indicies] 
        else:
            self.voltage_sets = [[(e, self.voltage_matrix[e][n]) for e in hc.elec_dict.keys()] for n in position_indicies] 
            
        if not loop: old_position = new_position

    def setDefault(self):
        self.multipoles = hc.default_multipoles
        self.position = 0
        self.multipole_matrix = {k: {j: [i/10. for i in range(1,11)] for j in self.multipoles} for k in hc.elec_dict.keys()}
        self.multipole_vector = {m: 0. for m in self.multipoles}
        self.num_columns = 10
        self.name = 'none_specified'

class Queue(object):
    def __init__(self):
        self.current_set = 1
        self.set_dict = {i: [] for i in range(1, hc.maxCache + 1)}

    def advance(self):
        self.current_set = (self.current_set % hc.maxCache) + 1

    def reset(self):
        self.current_set = 1

    def insert(self, v):
        ''' Always insert voltages to the current queue position '''
        v.program(self.current_set)
        self.set_dict[self.current_set].append(v)

    def get(self):        
        v = self.set_dict[self.current_set].pop(0)
        return v


class DACServer(LabradServer):
    """
    DAC Server
    Used for controlling DC trap electrodes
    """
    name = SERVERNAME
    onNewUpdate = Signal(SIGNALID, 'signal: ports updated', 's')
    onNewCfile = Signal(SIGNALID+1, 'signal: cfile updated', 's')
    queue = Queue()
    api = api()

    registry_path = ['', 'Servers', hc.EXPNAME + SERVERNAME]
    dac_dict = dict(hc.elec_dict.items() + hc.sma_dict.items())
    current_voltages = {}    
    listeners = set()

    @inlineCallbacks
    def initServer(self):
        print shuttle
        self.registry = self.client.registry
        self.initializeBoard()
        yield self.setCalibrations()
        try: yield self.setPreviousControlFile()
        except: yield self.setVoltagesZero()

    def initializeBoard(self):
        connected = self.api.connectOKBoard()
        if not connected:
            raise Exception ("FPGA Not Found")     

    @inlineCallbacks
    def setCalibrations(self):
        ''' Go through the list of sma outs and electrodes and try to detect calibrations '''
        yield self.registry.cd(self.registry_path + ['Calibrations'], True)
        subs, keys = yield self.registry.dir()
        print 'Calibrated channels: ', subs
        for chan in self.dac_dict.values():
            c = [] # list of calibration coefficients in form [c0, c1, ..., cn]
            if str(chan.dacChannelNumber) in subs:
                yield self.registry.cd(self.registry_path + ['Calibrations', str(chan.dacChannelNumber)])
                dirs, coeffs = yield self.registry.dir()
                for n in range( len(coeffs) ):
                    e = yield self.registry.get( 'c'+str(n) )
                    c.append(e)
                chan.calibration = c
            else:
                (vMin, vMax) = chan.boardVoltageRange
                prec = hc.PREC_BITS
                chan.calibration = [2**(prec - 1), float(2**(prec))/(vMax - vMin) ]
    
    @inlineCallbacks
    def setPreviousControlFile(self):        
        yield self.registry.cd(self.registry_path)
        Cfile_name = yield self.registry.get('most_recent_Cfile')
        yield self.setControlFile(0,Cfile_name)

    @inlineCallbacks
    def setPreviousVoltages(self):
        ''' Try to set previous voltages used with current Cfile '''
        yield self.registry.cd(self.registry_path + [self.control.name], True)
        
        try: multipole_vector = yield self.registry.get('multipole_vector')         
        except: multipole_vector = [(k, 0) for k in self.control.multipoles] # if no previous multipole values have been recorded, set them to zero.
        yield self.setMultipoleValues(0, multipole_vector)      
        
        yield self.registry.cd(self.registry_path + [self.control.name, 'sma_voltages'])
        for k in hc.sma_dict.keys():
            try: av = yield self.registry.get(k)
            except: av = 0. # if no previous voltage has been recorded, set to zero. 
            yield self.setIndividualAnalogVoltages(0, [(k, av)])        
   
    @inlineCallbacks
    def setVoltagesZero(self):
        yield self.registry.cd(self.registry_path + ['none_specified'], True)
        self.control = Control('none_specified')
        yield self.setIndividualAnalogVoltages(0, [(s, 0) for s in self.dac_dict.keys()])

    def writeToFPGA(self, c):
        self.api.resetFIFODAC()
        for i in range(len(self.queue.set_dict[self.queue.current_set])):
            v = self.queue.get() 
            self.api.setDACVoltage(v.hex_rep)
            print v.channel.name, v.analog_voltage
            self.current_voltages[v.channel.name] = v.analog_voltage
        self.notifyOtherListeners(c)
 
    @setting(0, "Set Control File", Cfile_path='s')
    def setControlFile(self, c, Cfile_path):
        self.control = Control(Cfile_path)
        yield self.setPreviousVoltages()
        yield self.registry.cd(self.registry_path)
        yield self.registry.set('most_recent_Cfile', Cfile_path)
        # self.notifyOtherListenersOfNewCfile(c)

    @setting( 1, "Set Multipole Values", multipole_vector='*(sv): dictionary of multipole values')
    def setMultipoleValues(self, c, multipole_vector):
        """
        Set new electrode voltages given a multipole set.
        """
        self.control.populateVoltageMatrix(multipole_vector)
        yield self.setIndividualAnalogVoltages(c, self.control.getVoltages())
        # Update registry
        if self.control.name:
            yield self.registry.cd(self.registry_path + [self.control.name], True)
            yield self.registry.set('multipole_vector', multipole_vector)

    @setting( 2, "Set Digital Voltages", digital_voltages='*v', set_num='i')
    def setDigitalVoltages( self, c, digital_voltages, set_num):
        """
        Pass digital_voltages, a list of digital voltages to update.
        Currently, there must be one for each port.
        """
        l = zip(self.dac_dict.keys(), digital_voltages)
        self.setIndivDigVoltages(c, l, set_num)

    @setting( 3, "Set Analog Voltages", analog_voltages='*v', set_num='i')
    def setAnalogVoltages( self, c, analog_voltages, set_num):
        """
        Pass analog_voltages, a list of analog voltages to update.
        Currently, there must be one for each port.
        """
        l = zip(self.dac_dict.keys(), analog_voltages)
        yield self.setIndivAnaVoltages(c, l, set_num)

    @setting( 4, "Set Individual Digital Voltages", digital_voltages='*(si)')
    def setIndividualDigitalVoltages(self, c, digital_voltages):
        """
        Pass a list of tuples of the form:
        (portNum, newVolts)
        """
        for (port, dv) in digital_voltages:
            self.queue.insert(Voltage(self.dac_dict[port], digital_voltage=dv))
        yield self.writeToFPGA(c)

    @setting( 5, "Set Individual Analog Voltages", analog_voltages='*(sv)')
    def setIndividualAnalogVoltages(self, c, analog_voltages):
        """
        Pass a list of tuples of the form:
        (portNum, newVolts)
        """
        for (port, av) in analog_voltages:
            self.queue.insert(Voltage(self.dac_dict[port], analog_voltage=av))
            if self.dac_dict[port].smaOutNumber and self.control.name:
                yield self.registry.cd(self.registry_path + [self.control.name, 'sma_voltages'], True)
                yield self.registry.set(port, av)
        yield self.writeToFPGA(c)
   
    @setting( 6, "Set First Voltages")
    def setFirstVoltages(self, c):
        self.queue.reset()
        yield self.setIndividualAnalogVoltages(c, self.control.getVoltages())

    @setting( 7, "Set Next Voltages")
    def setNextVoltages(self, c):
        self.queue.advance()
        yield self.setIndividualAnalogVoltages(c, self.control.getVoltages())

    @setting( 8, "Shuttle Arb", shuttle_parameters='?')
    def shuttleArb(self, c, shuttle_parameters):
        (new_position, step_size, duration, loop, loop_delay, overshoot) = shuttle_parameters
        self.control.getShuttleVoltagesArb(new_position, step_size, duration, loop, loop_delay, overshoot)
        
        for voltage_set in self.control.voltage_sets:
            self.queue.advance()
            voltage_set += [(s, self.current_voltages[s]) for s in hc.sma_dict.keys()]
            yield self.setIndividualAnalogVoltages(c, voltage_set)

        if self.control.name:
            yield self.registry.cd(self.registry_path + [self.control.name])
            yield self.registry.set('position', self.control.position)

        returnValue(self.control.times)

    @setting( 9, "Shuttle")
    def shuttle(self, c):   
        position = self.control.move_to
        step_size = yield self.client.parametervault.get_parameter('shuttle', 'step_size')
        duration = yield self.client.parametervault.get_parameter('shuttle', 'duration')
        loop = False 
        loop_delay = yield self.client.parametervault.get_parameter('shuttle', 'loop_delay')
        overshoot = yield self.client.parametervault.get_parameter('shuttle', 'overshoot')

        times = yield self.shuttleArb(c, (position, step_size, duration, loop, loop_delay, overshoot))
        yield self.client.parametervault.set_parameter('advanceDACs', 'times', times)
        print '1'
        experiment = shuttle()
        print '2'
        identity = yield self.client.scriptscanner.register_external_launch(experiment.name)
        print '3'
        experiment.execute(identity)
        print '4'

    @setting( 10, "Load")
    def load(self, c):
        lv = self.control.getLoadVoltages()
        print lv
        yield self.setIndividualAnalogVoltages(c, self.control.getLoadVoltages())

    @setting( 11, "Get Analog Voltages", returns='*(sv)' )
    def getCurrentVoltages(self, c):
        """
        Return the current voltage
        """
        return self.current_voltages.items()        

    @setting( 12, "Get Multipole Values",returns='*(s, v)')
    def getMultipoleValues(self, c):
        """
        Return a list of multipole voltages
        """
        return self.control.multipole_vector.items()

    @setting( 13, "Get Multipole Names",returns='*s')
    def getMultipoleNames(self, c):
        """
        Return a list of multipole voltages
        """
        return self.control.multipoles        

    @setting( 14, "Get Position", returns='i')
    def getPosition(self, c):
        return self.control.position

    @setting( 15, "Get Cfile Info", returns='bs*s')
    def getCfileInfo(self, c):
        Cfile_list = os.listdir('Cfiles')
        if self.control.num_columns > 1: shuttle_on = True
        else: shuttle_on = False
        return (shuttle_on, self.control.name, Cfile_list) 

    def initContext(self, c):
        self.listeners.add(c.ID)

    def expireContext(self, c):
        self.listeners.remove(c.ID)
    
    def notifyOtherListeners(self, context):
        notified = self.listeners.copy()
        try: notified.remove(context.ID)
        except: pass
        self.onNewUpdate('Channels updated', notified)

    def notifyOtherListenersOfNewCfile(self, c):
        notified = self.listeners.copy()
        notified.remove(c.ID)
        # self.onNewCfile('Cfile updated', notified)

if __name__ == "__main__":
    from labrad import util
    util.runServer( DACServer() )

"""
Notes for DACSERVER:

example of a Cfile corresponding to a trap w/ 23 electrodes, 4 multipole values, and (axial) trap position of 850um:

multipoles: Ex, Ey, Ez, U2
Ex_1
Ex_2
.
.
.
Ex_23
Ey_1
.
.
.
U2_23
850

The first line, "multipoles: Ex, ...", lets you specify a unique set of multipoles for each Cfile. It is optional.
If you choose not to include it, the server will instead use the default multipoles specified in DacConfiguration.py


If you intend to do shuttling, place Cfiles next to each other:

multipoles: Ex, Ey, Ez, U2
default position: 875
Ex_1.1   Ex_1.2
Ex_2.1   Ex_2.2
.        .
.        .
.        .
Ex_23.1  .
Ey_1.1   .
.        .
.        .
.        .
U2_23.1  U2_23.2
850      900

"default position: 875" specifies the default ion position. As of now, in order to specify "default position", a "multipolipoles" entry must come first.
"""

