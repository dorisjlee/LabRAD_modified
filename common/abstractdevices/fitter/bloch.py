# from __future__ import division
from scipy.optimize import *
from get_data import *
import lmfit as lmfit 
from datafit import DataFit
import numpy as np
from scipy.integrate import odeint
import math
class Bloch(DataFit):
    name = 'Bloch'
    def __init__(self):
        DataFit.__init__(self)
        self.excitation_time=0
        self.all_parameters=['t_excitation', 'height','gamma','ohm','shift']
        self.guess_dict={ 't_excitation': lambda : 10.0 , 
			'height': self.guess_height	,
            'shift': lambda : 0.0,
            'gamma': lambda :  1e-4     ,
            'ohm': lambda: 2*np.pi*1000
			}
        # Is this necessary?
        #self.parameters = self.guess_dict
        # self.raw= raw
        # self.setData(raw)
    
    def guess(self, param):
        return self.guess_dict[param]()

    # def guess_ohm
    # def guess_gamma
    def guess_height(self):
    # Not Necessary?
	# max at zero corrsponds to multiplicative coeficient
        return max(self.dataY)

    def guess_shift(self):
        #algorithm that finds the time (x value) corresponding to max height (ymax) 
        shift =0.0
        for i in range(len(self.dataX)):
            # print("here")
            if (self.dataY[i]==max(self.dataY)):
                shift= self.dataX[i]
                # print("here2")
        return (shift)
        
    def model (self,params,x):
        # LOOK AT PARAMETER USED IN lorentizian.py
        #Parameter 
        t_excitation = params['t_excitation'].value
        height = params['height'].value
        shift = params['shift'].value
        gamma = params['gamma'].value
        #width = param ['width'].value
        # k = 2*np.pi***2*t_excitation
	    #Calculating width coefficient 
        # model = height* np.sin(kx)/x
        exc = []
        #step = math.floor((50*ohm)*2/len(x)-1) #Need to truncate this value
        step=(50*ohm)*2/(len(x))
        # # You want to scan delta over the whole range but also want to keep the delta_list (which is the size of Y model data)
        # # the same size as the Xdata
        # # delta_list = np.arange(-50*ohm, 50*ohm, 2000)
        # print (step)
        delta_list = np.arange(-50*ohm, 50*ohm, step)
        # # delta_list = np.arange(len(x))
        # print (len(delta_list))
        for delta_i in delta_list:
            # exc.append(height*(blochSolver(delta_i, gamma = 1e-4)+1)/2)
            # print (delta_i)
            r3 = height*((blochSolver(delta_i+shift, gamma = gamma,T_0=t_excitation)+1)/2)
            exc.append(r3)
        # # plt.plot(delta_list, exc)
        # print (len(exc))
        # # print (exc)
        return exc

ohm = 2*np.pi*1000 #Hz
#T_1 is now called gamma
# gamma is a parameter that determines damping on r3
gamma = 1e-5 #Set T as infinite (large)
# We don't care about T_2, it is taken to be very small
# T_2 = 2*T_1

#Initial Condition (In z direction, initially R_3= -1)
R0 = [0,0,-1]

T_2pi = 10. #excitation time 
# How to make T vary in here ? 
def blochSolver(delta, gamma = 1, T_0 = 0.6/ohm):
    def f(R, t):
        #pass
        r1 = R[0]
        r2 = R[1]
        r3 = R[2]
        # print delta
        # Coupled ODE, as 3 different functions 
        # don't consider any T2
        f1 = - delta*r2
        f2 = delta*r1 + ohm*r3
        f3 = - r3/gamma -ohm*r2
        return [f1,f2,f3]
    t = np.linspace(0, T_0,50) # Time evolution
    # Minimize mxstep, if too large then Integration unsucessful.
    sol = odeint(f, R0, t,mxstep=350000)#,full_output=1) 
    # print ("sol:"+str(sol))
    r3 = sol[0][:,2]
    print (r3)
    return r3[-1]

	


