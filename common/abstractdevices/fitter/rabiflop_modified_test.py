'''
Testing modification to guess_f_rabi and 
Container class for a Rabi flop fit

'''
import lmfit as lmfit
from datafit import DataFit
import numpy as np
import timeevolution as te
from labrad import units as U
from get_data import * # get_data files not in working dir, only in lab machine 
# import sys
# sys.path.append('Haeffner-Lab-LabRAD-Tools/dataAnalysis/rabi_flop_fitter/')
# from Haeffner-Lab-LabRAD-Tools.dataAnalysis.rabi_flop_fitter.rabi_flop_fitter 
from rabi_flop_fitter_modified_test  import rabi_flop_time_evolution
class RabiFlop(DataFit):
    def __init__(self, raw):
        DataFit.__init__(self)
        # Function form
        self.guess_dict = {'nbar':lambda : 5.0, 'f_rabi':   self.guess_f_rabi,
                           'delta': lambda : 0.0 , 'delta_fluctuations': lambda : 0.0, 
                          'trap_freq':lambda :  1.0e6, 'sideband': lambda:0.0,
                           'nmax': lambda: 1000, 'angle': lambda : np.pi/4, #'projection': lambda: np.pi/4 ,
                           'rabi_type':lambda:'coherent', 'eta': self.guess_eta}#eta=0.05 
        self.parameters = self.guess_dict
        self.raw = raw
        self.setData(raw)

    def guess(self, param):
        return self.guess_dict[param]()
    
    def guess_f_rabi(self):
        #print self.raw[:,1]
    	count =0 
    	threshold = 0.8 
    	curve= False
    	tmp =[]
    	for i in range(self.raw[:,1].size):
            if count <1 :
            	if self.raw[:,1][i]< threshold:
                    if curve != False: # comparing the previous value to current one for detecting change
                        #print "crossing"
                 	count +=1
                    curve = False
                #print False
            	else:
                    #if curve != True: #detect change
                    #print "crossing" 
                    curve = True
                #print True
            	tmp.append(self.raw[:,1][i])
            else:
            	break
    	max(tmp)
    	val=0
    	for i in range(len(tmp)):
     	    if tmp[i] == max(tmp):
            	val=i
    	val=self.raw[val][0]
    	#print (val)
	return 1/(val*2e-5*np.power(self.guess_dict['eta'](),abs(self.guess_dict['sideband']())))
	
    def guess_eta(self):
	return 2*np.pi/(729e-9)*np.sqrt(1.054571e-34/(2*40*(1.67262178e-27)*(2*np.pi*self.guess_dict['trap_freq']())))*np.cos(self.guess_dict['angle']())
    
    def model (self,params,x):
    	# Because we are inheriting from datafit.py
    	# model only takes 2 parameter  model(params,x)
        #print 'the length of x is' + str(len(x))
        #eta=0.05
        #eta = params['eta'].value
	nbar = params['nbar'].value 
        #nbar =5
        delta = params['delta'].value
        # delta_fluct = params['delta_fluctuations'].value
        trap_freq = params['trap_freq'].value
        sideband = params['sideband'].value
        nmax = params['nmax'].value
        angle= params['angle'].value
        rabi_type = params['rabi_type'].value
        eta = params['eta'].value
	f_rabi = params['f_rabi'].value
	flop_te  = rabi_flop_time_evolution(sideband,eta,nmax)
    	# (self, sideband_order, eta, nmax = 1000):
	# flop = te.time_evolution(trap_frequency = U.WithUnit(trap_freq, 'MHz'), projection = projection, sideband_order = sideband, nmax = nmax)
        # x is the (excitation)time in microseconds
        #print "f_rabi guess: " + str(self.guess_f_rabi())
        #print "T_2pi: " + str(1./self.guess_f_rabi())
        if (params['rabi_type']=='coherent' ):
            #set alpha =100
            #return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./self.guess_f_rabi(), x*10e-6)
	    return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./f_rabi , x*10e-6)
        elif (params['rabi_type']== 'thermal'):
            #return flop_te.compute_evolution_thermal(nbar, delta, 1./self.guess_f_rabi() , x*10e-6)
	    return flop_te.compute_evolution_thermal(nbar, delta, 1./f_rabi , x*10e-6)

            #1/(x*2e-6)
	flop_te  = rabi_flop_time_evolution(sideband,eta,nmax)
    	# (self, sideband_order, eta, nmax = 1000):
	# flop = te.time_evolution(trap_frequency = U.WithUnit(trap_freq, 'MHz'), projection = projection, sideband_order = sideband, nmax = nmax)
        # x is the (excitation)time in microseconds
        #print "f_rabi guess: " + str(self.guess_f_rabi())
        #print "T_2pi: " + str(1./self.guess_f_rabi())
        if (params['rabi_type']=='coherent' ):
            #set alpha =100
            #return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./self.guess_f_rabi(), x*10e-6)
	    return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./f_rabi , x*10e-6)
        elif (params['rabi_type']== 'thermal'):
            #return flop_te.compute_evolution_thermal(nbar, delta, 1./self.guess_f_rabi() , x*10e-6)
	    return flop_te.compute_evolution_thermal(nbar, delta, 1./f_rabi , x*10e-6)

            #1/(x*2e-6)
        rabi_type = params['rabi_type'].value
        eta = params['eta'].value
	f_rabi = params['f_rabi'].value
	flop_te  = rabi_flop_time_evolution(sideband,eta,nmax)
    	# (self, sideband_order, eta, nmax = 1000):
	# flop = te.time_evolution(trap_frequency = U.WithUnit(trap_freq, 'MHz'), projection = projection, sideband_order = sideband, nmax = nmax)
        # x is the (excitation)time in microseconds
        #print "f_rabi guess: " + str(self.guess_f_rabi())
        #print "T_2pi: " + str(1./self.guess_f_rabi())
        if (params['rabi_type']=='coherent' ):
            #set alpha =100
            #return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./self.guess_f_rabi(), x*10e-6)
	    return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./f_rabi , x*10e-6)
        elif (params['rabi_type']== 'thermal'):
            #return flop_te.compute_evolution_thermal(nbar, delta, 1./self.guess_f_rabi() , x*10e-6)
	    return flop_te.compute_evolution_thermal(nbar, delta, 1./f_rabi , x*10e-6)

            #1/(x*2e-6)
        rabi_type = params['rabi_type'].value
        eta = params['eta'].value
	f_rabi = params['f_rabi'].value
	flop_te  = rabi_flop_time_evolution(sideband,eta,nmax)
    	# (self, sideband_order, eta, nmax = 1000):
	# flop = te.time_evolution(trap_frequency = U.WithUnit(trap_freq, 'MHz'), projection = projection, sideband_order = sideband, nmax = nmax)
        # x is the (excitation)time in microseconds
        #print "f_rabi guess: " + str(self.guess_f_rabi())
        #print "T_2pi: " + str(1./self.guess_f_rabi())
        if (params['rabi_type']=='coherent' ):
            #set alpha =100
            #return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./self.guess_f_rabi(), x*10e-6)
	    return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./f_rabi , x*10e-6)
        elif (params['rabi_type']== 'thermal'):
            #return flop_te.compute_evolution_thermal(nbar, delta, 1./self.guess_f_rabi() , x*10e-6)
	    return flop_te.compute_evolution_thermal(nbar, delta, 1./f_rabi , x*10e-6)

            #1/(x*2e-6)
        # Can add additional types here later .
        else:
            raise ValueError('Rabi Flop type must be either coherent or thermal')
        #model = flop.state_evolution_fluc(x*10**-6, nbar, f_rabi, delta, delta_fluct, n_fluc = 5.0 )
        # (t,nbar,f_Rabi,delta_center,delta_variance,n_fluc=5.0)
        #return model
'''
def coherent_tester():        
    dataobj = ReadData('2014May27',experiment = 'RabiFlopping') 
    car_data = dataobj.get_data('1447_53')
    rabi = RabiFlop(car_data) #default set as 'coherent'
    rabi.setData(car_data)
    #print(rabi.guess_f_rabi())
    params = lmfit.Parameters()
    params.add('eta',value=0.01)
    params.add('nbar', value = 5.0 )
    params.add('f_rabi', value = rabi.guess_f_rabi())
    params.add('delta', value = 0.0)
    params.add('delta_fluctuations', value = 0.0)
    params.add('trap_freq', value =1.0)
    params.add('sideband',value = 0.0)
    params.add('nmax',value = 1000 )
    params.add('angle',value = np.pi/4)
    params.add('rabi_type',value='coherent')
    rabi.setUserParameters(params)
    # rabi.model(rabi.parameters, [int (i) for i in np.linspace(0,50)])
    # rabi.model(rabi.parameters,np.arange(50))
    # Let eta =0.05
    #rabi.model(params['nbar'].value,0.05,params,np.arange(50))
    # must be the same size as nmax 
    #rabi.model(params['nbar'].value,0.05,params,np.arange(1000))
    rabi.model(params, np.arange(1000)) 

#coherent_tester()
'''


def thermal_tester():
        import matplotlib.pyplot as plt
	dataobj = ReadData('2014Jun19',experiment = 'RabiFlopping' )
        car_data = dataobj.get_data('1219_57')
        sideband = 0
        trap_freq =  2.57
        nbar_init= 0.1 #default 20.
        carrier_rabi = RabiFlop(car_data)
        #carrier_rabi.setData(car_data)
#         val=0
#         for i in range(car_data[:,1].size):
#             if car_data[:,1][i] == max(car_data[:,1]):
#                 val=i
#         val=car_data[val][0]
        initial_guess = {'nbar':nbar_init, 'f_rabi':carrier_rabi.guess_f_rabi(),  #changing inital guess for rabi frequency to 1/2 max 
                             'delta':0., 'delta_fluctuations':0.,
                              'trap_freq':trap_freq, 'sideband':sideband, 'nmax':1000,
                              'angle':10./360.*2*np.pi  , 'rabi_type':'thermal'
                        ,'eta': 0.05 }
        fit_params = {}
        #Put it in the fit params format 
        for key in initial_guess.keys():
            fit_params[key] = (False, False, initial_guess[key]) # fix most of the parameters
        fit_params['f_rabi'] = (True, False, initial_guess['f_rabi']) # fit for the rabi frequency
        carrier_rabi.setUserParameters(fit_params)
        x,y = carrier_rabi.fit()
        plt.figure()
        plt.plot(car_data[:,0], car_data[:,1],'o') # plotting raw data : excitation probability versus time
        plt.plot(x,y) #plotting the fit
        #print carrier_rabi.get_parameter_info()
        print carrier_rabi.get_parameter_info()['f_rabi'][2][2] #this is the autofit result
        #get_parameter_value returns the user_guess result
        #f_rabi = carrier_rabi.get_parameter_value('f_rabi') # rabi frequency in Hz
        f_rabi = carrier_rabi.get_parameter_info()['f_rabi'][2][2] #autofit result
        return f_rabi

thermal_tester()

def blue_sideband_thermal_tester():
        #BSB sideband = +1
        import matplotlib.pyplot as plt
	dataobj = ReadData('2014Jun19',experiment = 'RabiFlopping' )
        data = dataobj.get_data('1212_15')
        sideband = 1
        trap_freq =  2.57
        nbar_init= .3 #default 20.
        rabi = RabiFlop(data)
        rabi.setData(data)
        f_rabi = thermal_tester() #f_rabi is the same on same set of data
        print("f_rabi from thermal tester is :"+str(f_rabi))
        initial_guess = {'nbar':nbar_init, 'f_rabi':f_rabi,  #same as that of thermal tester
                             'delta':0.0, 'delta_fluctuations':0.,
                              'trap_freq':trap_freq, 'sideband':sideband, 'nmax':1000,
                              'angle': 50./360.*2*np.pi, 
                              'rabi_type':'thermal','eta': 0.04 #rabi.guess_eta()#0.05
                        }
        fit_params = {}
        #Put it in the fit params format 
        for key in initial_guess.keys():
            fit_params[key] = (False, False, initial_guess[key]) # fix most of the parameters
        #fit_params['f_rabi'] = (False, False, f_rabi)#initial_guess['f_rabi']) # fit for the rabi frequency
        fit_params['nbar'] = (False, False, initial_guess['nbar'])
        fit_params['angle'] = (True, False, initial_guess['angle'])
        #fit_params['delta'] = (True, False, initial_guess['delta'])
        rabi.setUserParameters(fit_params)
        x,y = rabi.fit()
        plt.figure()
        plt.plot(data[:,0], data[:,1],'o') # plotting raw data : excitation probability versus time
        plt.plot(x,y) #plotting the fit
        nbar = rabi.get_parameter_value('nbar') # rabi frequency in Hz
        angle= rabi.get_parameter_value('angle')
        #print rabi.get_parameter_info()
        print ('nbar: {}'.format(nbar))
        print ('{} radians = {} degrees'.format(str(angle), str(angle/(2*np.pi)*360)))

blue_sideband_thermal_tester()

