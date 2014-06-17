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
        #def __init__(self):    
        DataFit.__init__(self)
        #self.guess_dict = {'nbar': 5.0, 'f_rabi': self.guess_f_rabi,
        #                   'delta': 0.0 , 'delta_fluctuations': 0.0,
        #                  'trap_freq': 1.0, 'sideband': 0.0,
        #                   'nmax': 1000, 'projection': np.pi/4 ,'rabi_type':'coherent'} 
        # Function form
        self.guess_dict = {'nbar':lambda : 5.0, 'f_rabi':   self.guess_f_rabi,
                           'delta': lambda : 0.0 , 'delta_fluctuations': lambda : 0.0, 
                          'trap_freq':lambda :  1.0e6, 'sideband': lambda:0.0,
                           'nmax': lambda: 1000, 'angle': lambda : np.pi/4, #'projection': lambda: np.pi/4 ,
                           'rabi_type':lambda:'coherent', 'eta': self.guess_eta}#eta=0.05 
        #self.get_parameter_value('type') is either 'coherent' or 'thermal'
        #self.parameters = self.guess_dict.keys()
        self.parameters = self.guess_dict
        self.raw = raw
        self.setData(raw)
        #params = lmfit.Parameters()
        #params.add('nbar', value = 5.0 )
        #params.add('f_rabi', value = self.guess_f_rabi())
        #params.add('delta', value = 0.0)
        #params.add('delta_fluctuations', value = 0.0)
        #params.add('trap_freq', value =1.0)
        #params.add('sideband',value = 0.0)
        #params.add('nmax',value = 1000 )
        #params.add('projection',value = np.pi/4)
        #params.add('rabi_type',value='coherent')
        #self.setUserParameters(params)
    def guess(self, param):
        return self.guess_dict[param]()
    
    def guess_f_rabi(self):
    #Assume "raw" has form of 3 columns [x,y,error] where x = time and y = excitation probability
        for i in range(self.raw[:,1].size):
            if self.raw[:,1][i] == max(self.raw[:,1]):
                val=self.raw[i][0]
                # converting this time value to freq (reciprocal)
                # convert millisec => mHz => Hz
#        return 1/(val*2e-6)
        return 1/(val*2e-5*np.power(self.guess_dict['eta'](),abs(self.guess_dict['sideband']())))    
    #def model(self,nbar,eta, params, x):
    def guess_eta(self):
	return 2*np.pi/(729e-9)*np.sqrt(1.054571e-34/(2*40*(1.67262178e-27)*(2*np.pi*self.guess_dict['trap_freq']())))*np.cos(self.guess_dict['angle']())
    def model (self,params,x):
    	# Because we are inheriting from datafit.py
    	# model only takes 2 parameter  model(params,x)
        print 'the length of x is' + str(len(x))
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
        flop_te  = rabi_flop_time_evolution(sideband,eta,nmax)
    	# (self, sideband_order, eta, nmax = 1000):
		# flop = te.time_evolution(trap_frequency = U.WithUnit(trap_freq, 'MHz'), projection = projection, sideband_order = sideband, nmax = nmax)
        # x is the (excitation)time in microseconds
        print "f_rabi guess: " + str(self.guess_f_rabi())
        #print "T_2pi: " + str(1./self.guess_f_rabi())
        if (params['rabi_type']=='coherent' ):
            #set alpha =100
            return flop_te.compute_evolution_coherent(nbar, 3, delta, 1./self.guess_f_rabi(), x*10e-6)
        elif (params['rabi_type']== 'thermal'):
            return flop_te.compute_evolution_thermal(nbar, delta, 1./self.guess_f_rabi() , x*10e-6)
            #1/(x*2e-6)
        # Can add additional types here later .
        else:
            raise ValueError('Rabi Flop type must be either coherent or thermal')
        #model = flop.state_evolution_fluc(x*10**-6, nbar, f_rabi, delta, delta_fluct, n_fluc = 5.0 )
        # (t,nbar,f_Rabi,delta_center,delta_variance,n_fluc=5.0)
        #return model

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

def thermal_tester():
    dataobj = ReadData('2014May27',experiment = 'RabiFlopping') 
    car_data3 = dataobj.get_data('1525_11')
    rabi3 = RabiFlop(car_data3) #default set as 'coherent'
    rabi3.setData(car_data3)
    print(rabi3.guess_f_rabi())
    params = lmfit.Parameters()
    params.add('eta',value =0.01)
    params.add('nbar', value = 3.0 ) #5.0
    params.add('f_rabi', value = rabi3.guess_f_rabi())
    params.add('delta', value = 0.0)
    params.add('delta_fluctuations', value = 0.0)
    params.add('trap_freq', value =2.0)  # 1.0
    params.add('sideband', value = 0.0)
    params.add('nmax',value = 800 ) #1000
    params.add('angle',value = np.pi/4)
    params.add('rabi_type',value='thermal')
    rabi3.setUserParameters(params)
    #rabi3.model(params['nbar'].value,0.05,params,np.arange(800))
    rabi3.model(params,np.arange(800))

#thermal_tester()


def third_sideband_thermal_tester():
    dataobj = ReadData('2014May27',experiment = 'RabiFlopping') 
    car_data2 = dataobj.get_data('1525_11')
    rabi2 = RabiFlop(car_data2) #default set as 'coherent'
    rabi2.setData(car_data2)
    print('guess rabi:'+str(rabi2.guess_f_rabi()))
    params = lmfit.Parameters()
    print ('guess eta:'+str(rabi2.guess_eta()))
    #params.add('eta',value =0.01)#rabi2.guess_eta())#0.01
    params.add('nbar', value = 3.0 ) #5.0
    params.add('f_rabi', value = rabi2.guess_f_rabi())
    params.add('delta', value = 0.0)
    params.add('delta_fluctuations', value = 0.0)
    params.add('trap_freq', value =2.0)  # 1.0
    params.add('sideband', value = 3.0)
    params.add('nmax',value = 800 ) #1000
    params.add('angle',value = np.pi/4)
    params.add('rabi_type',value='thermal')
    #params.add('eta',value=0.01)
    #print (rabi2.guess_eta()**2)
    print (rabi2.guess_eta())
    eta = rabi2.guess_eta()
    n=3
    from scipy.special.orthogonal import eval_genlaguerre as laguerre
    #print 'result: '+ str(abs(1e2*np.exp(-1./2.*eta**2.)*eta**(3.)*(1./((n+1.)*(n+2.)*(n+3.)))**0.5*laguerre(n,3.,eta**2.)))
    #np.exp(-1./2*eta**2) * eta**(3)*(1./((n+1)*(n+2)*(n+3)))**0.5 * laguerre(n, 3 , eta**2)
    #print 'result: '+ str((1e2*np.exp(-1./2.*eta**2.)*eta**(3.)*(1./((n+1.)*(n+2.)*(n+3.)))**0.5*laguerre(n,3.,eta**2.))=='NaN')
    #print ('result: '+ str(abs(np.exp(-1./2.*eta**2.)*eta**(3.)*(1./((n+1.)*(n+2.)*(n+3.)))**0.5*laguerre(n,3.,eta**2.))))
    params.add('eta',value=rabi2.guess_eta())
    #eta= rabi2.guess_eta()
    #print eta
    #params.add('eta',value =eta)#rabi2.guess_eta())#0.01
    rabi2.setUserParameters(params)
    #rabi2.model(params['nbar'].value,0.05,params,np.arange(800))
    rabi2.model(params,np.arange(800))

#third_sideband_thermal_tester()


'''def fifth_sideband_thermal_tester():
    dataobj = ReadData('2014May27',experiment = 'RabiFlopping')
    car_data3 = dataobj.get_data('1525_11')
    rabi3 = RabiFlop(car_data3) #default set as 'coherent'
    rabi3.setData(car_data3)
    print(rabi3.guess_f_rabi())
    params = lmfit.Parameters()
    params.add('eta',value =rabi3.guess_eta())
    params.add('nbar', value = 3.0 ) #5.0
    params.add('f_rabi', value = rabi3.guess_f_rabi())
    params.add('delta', value = 0.0)
    params.add('delta_fluctuations', value = 0.0)
    params.add('trap_freq', value =2.0)  # 1.0
    params.add('sideband', value = 0.0)
    params.add('nmax',value = 800 ) #1000
    params.add('angle',value = np.pi/4)
    params.add('rabi_type',value='thermal')
    rabi3.setUserParameters(params)
    #rabi2.model(params['nbar'].value,0.05,params,np.arange(800))
    rabi3.model(params,np.arange(800))
fifth_sideband_thermal_tester()'''
