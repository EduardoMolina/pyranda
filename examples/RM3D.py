import re
import sys
import time
import numpy 
import matplotlib.pyplot as plt
from matplotlib import cm

from pyranda import pyrandaSim, pyrandaBC, pyrandaTimestep


# Try to get args for testing
try:
    Npts = int(sys.argv[1])
except:
    Npts = 32

try:
    test = bool(int(sys.argv[2]))
except:
    test = False

problem = 'RM_theta'

## Define a mesh
Npts = 64
imesh = """
xdom = (0.0, 2.8*pi , int(Npts*1.4), periodic=False) 
ydom = (0.0, 2*pi*FF,  Npts, periodic=True)
zdom = (0.0, 2*pi*FF,  1, periodic=True)
""".replace('Npts',str(Npts)).replace('pi',str(numpy.pi)).replace('FF',str( float(Npts-1)/Npts ) )

    
# Initialize a simulation object on a mesh
ss = pyrandaSim(problem,imesh)
ss.addPackage( pyrandaTimestep(ss) )
ss.addPackage( pyrandaBC(ss) )

# Define the equations of motion
eom ="""
# Primary Equations of motion here
ddt(:rhoYh:)  =  -ddx(:rhoYh:*:u: - :Jx:)    - ddy(:rhoYh:*:v: - :Jy:)   - ddz(:rhoYh:*:w: - :Jz:)
ddt(:rhoYl:)  =  -ddx(:rhoYl:*:u: + :Jx:)    - ddy(:rhoYl:*:v: + :Jy:)   - ddz(:rhoYl:*:w: + :Jz:)
ddt(:rhou:)   =  -ddx(:rhou:*:u: - :tauxx:)  - ddy(:rhou:*:v: - :tauxy:) - ddz(:rhou:*:w: - :tauxz:)
ddt(:rhov:)   =  -ddx(:rhov:*:u: - :tauxy:)  - ddy(:rhov:*:v: - :tauyy:) - ddz(:rhov:*:w: - :tauyz:)
ddt(:rhow:)   =  -ddx(:rhow:*:u: - :tauxz:)  - ddy(:rhow:*:v: - :tauyz:) - ddz(:rhow:*:w: - :tauzz:)
ddt(:Et:)     =  -ddx( (:Et: - :tauxx:)*:u: - :tauxy:*:v: - :tauxz:*:w: ) - ddy( (:Et: - :tauyy:)*:v: -:tauxy:*:u: - :tauyz:*:w:) - ddz( (:Et: - :tauzz:)*:w: - :tauxz:*:u: - :tauyz:*:v: )
# Conservative filter of the EoM
:rhoYh:     =  fbar( :rhoYh:  )
:rhoYl:     =  fbar( :rhoYl:  )
:rhou:      =  fbar( :rhou: )
:rhov:      =  fbar( :rhov: )
:rhow:      =  fbar( :rhow: )
:Et:        =  fbar( :Et:   )
# Update the primatives and enforce the EOS
:rho:       = :rhoYh: + :rhoYl:
:Yh:        =  :rhoYh: / :rho:
:Yl:        =  :rhoYl: / :rho:
:u:         =  :rhou: / :rho:
:v:         =  :rhov: / :rho:
:w:         =  :rhow: / :rho:
:p:         =  ( :Et: - .5*:rho:*(:u:*:u: + :v:*:v: + :w:*:w:) ) * ( :gamma: - 1.0 )
# Artificial bulk viscosity / shear viscosity
:ux:        =  ddx(:u:)
:vy:        =  ddy(:v:)
:wz:        =  ddz(:w:)
:div:       =  :ux: + :vy: + :wz:
# Remaining cross derivatives
:uy:        =  ddy(:u:)
:uz:        =  ddz(:u:)
:vx:        =  ddx(:v:)
:vz:        =  ddz(:v:)
:wy:        =  ddy(:w:)
:wx:        =  ddx(:w:)
:Yx:        =  ddx(:Yh:)
:Yy:        =  ddy(:Yh:)
:Yz:        =  ddz(:Yh:)
:enst:      = sqrt( (:uy:-:vx:)**2 + (:uz: - :wx:)**2 + (:vz:-:wy:)**2 )
:tke:       = :rho:*(:u:*:u: + :v:*:v: + :w:*:w:)
:S:         = sqrt( :ux:*:ux: + :vy:*:vy: + :wz:*:wz: + .5*((:uy:+:vx:)**2 + (:uz: + :wx:)**2 + (:vz:+:wy:)**2) )
:mu:        =  gbar( abs(ring(:S:  )) ) * :rho: * 1.0e-4
:beta:      =  gbar( abs(ring(:div:)) * :rho: )  * 7.0e-3
# Artificial species diffusivities
:Dsgs:      =  ring(:Yh:) * 1.0e-4
:Ysgs:      =  1.0e2*(abs(:Yh:) - 1.0 + abs(1.0-:Yh: ) )*:dx:**2
:adiff:     =  gbar( :rho:*max(:Dsgs:,:Ysgs:) / :dt: )
:Jx:        =  :adiff:*:Yx:
:Jy:        =  :adiff:*:Yy:
:Jz:        =  :adiff:*:Yz:
:taudia:    =  (:beta:-2./3.*:mu:) *:div:
:tauxx:     =  2.0*:mu:*:ux:   + :taudia: - :p:
:tauyy:     =  2.0*:mu:*:vy:   + :taudia: - :p:
:tauzz:     =  2.0*:mu:*:wz:   + :taudia: - :p:
:tauxy:     = :mu:*(:uy:+:vx:) 
:tauxz:     = :mu:*(:uz:+:wx:) 
:tauyz:     = :mu:*(:vz:+:wz:) 
:cs:        = sqrt( :p: / :rho: * :gamma: )
# Time step control routines
:dt:        = dt.courant(:u:,:v:,:w:,:cs:)*1.0
:dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:beta:,:rho:))
:dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:mu:,:rho:))
:dt:        = numpy.minimum(:dt:,0.2 * dt.diff(:adiff:,:rho:))
# Add some BCs in the x-direction
bc.const(['Yh'],['xn'],0.0)
bc.const(['Yh'],['x1'],1.0)
bc.const(['Yl'],['x1'],0.0)
bc.const(['Yl'],['xn'],1.0)
bc.extrap(['rho','Et'],['x1','xn'])
bc.extrap(['u'],['x1','xn'])
bc.const(['v','w'],['x1','xn'],0.0)
# Sponge BCs
:leftBC:  = 1.0 - 0.5 * (1.0 + tanh( (meshx-1.0) / .1 ) )
:rightBC: = 0.5 * (1.0 + tanh( (meshx-8.0) / .1 ) )
:BC: = max(:leftBC:,:rightBC:)
:u: = gbar(:u:)*:BC: + :u:*(1.0 - :BC:)
:rho: = gbar(:rho:)*:BC: + :rho:*(1.0 - :BC:)
:Et: = gbar(:Et:)*:BC: + :Et:*(1.0 - :BC:)
:rhoYh: = :rho:*:Yh:
:rhoYl: = :rho:*:Yl:
:rhou: = :rho:*:u:
:rhov: = :rho:*:v:
:rhow: = :rho:*:w:
"""

# Add the EOM to the solver
ss.EOM(eom)

# Initialize variables
ic = """
:gamma:= 5./3.
L      =  6.0
delta  = 2.0*numpy.pi / 32.0  * 2 
u0     = -291.575
p0     = 100000.0
rho0_h = 3.0
rho0_l = 1.0
rhoS   = 6.37497
uS     = -61.48754
pS     = 399995.9 
:dx: = 0.0

# Add perturbation
Amp = 3.5 + .05*(sin(meshy*L) ) #+cos(meshz*L))
:Yh: = .5 * (1.0-tanh( sqrt(numpy.pi)*( meshx - Amp) / delta ))
:Yl: = 1.0 - :Yh:
:p:  += p0 

# Add shock
:v: *= 0.0
:w: *= 0.0
:u: = gbar( where( meshx < 3.0, uS, u0) )
:rho: = gbar( where( meshx < 3.0, rhoS, rho0_h ) )
:rho: = where( meshx < 3.2, :rho:, rho0_h * :Yh: + rho0_l * :Yl:)
:p: = gbar( where( meshx < 3.0, pS, :p: ) )

# Form conserved quatities
:rhoYh: = :rho:*:Yh:
:rhoYl: = :rho:*:Yl:
:rhou: = :rho:*:u:
:rhov: = :rho:*:v:
:rhow: = :rho:*:w:
:Et:  = :p: / (:gamma:-1.0) + 0.5*:rho:*(:u:*:u: + :v:*:v: + :w:*:w:)
:cs:  = sqrt( :p: / :rho: * :gamma: )
:tke: = :rho:*(:u:*:u: + :v:*:v: + :w:*:w:)
:dt: = dt.courant(:u:,:v:,:w:,:cs:)
"""

#import pdb
#pdb.set_trace()


# Set the initial conditions
ss.setIC(ic)
    
# Length scale for art. viscosity
# Initialize variables
x = ss.mesh.coords[0]
y = ss.mesh.coords[1]
z = ss.mesh.coords[2]

# Set the value for dx
dx = x[1,0,0] - x[0,0,0]
ss.variables['dx'].data = dx


# Write a time loop
time = 0.0
viz = True

# Approx a max dt and stopping time


# Mesh for viz on master
xx   =  ss.PyMPI.zbar( x ) / Npts
yy   =  ss.PyMPI.zbar( y ) / Npts
#xx   =   x[:,:,16] / Npts
#yy   =   y[:,:,16] / Npts
ny = ss.PyMPI.ny

# Start time loop
CFL = 1.0
dt = ss.variables['dt'].data * CFL

# Viz
cnt = 1
viz_freq = 10
pvar = 'Yh'

tke0 = ss.var('tke').sum()
#enst0 = ss.var('enst').sum()
TKE = []
#ENST = []
TIME = []

tstop = 1.0
if test:
    tstop = .1

leftOn = False
rightOn = False

v   = ss.variables['v'].data
plt.contourf( v[:,:,0] )

#aa = raw_input("Step ...")

dtmax = dt * .1

while time < tstop:

    # Update the EOM and get next dt
    time = ss.rk4(time,dt)
    dt = ss.variables['dt'].data * CFL
    dt = min( dt, dtmax*1.1)
    dtmax = dt*1.0
    

    # Print some output
    tke = ss.var('tke').sum()/tke0
    #enst = ss.var('enst').sum()/enst0

    TIME.append(time)
    #ENST.append(enst)
    TKE.append(tke)

    #aa = raw_input("Step ...")
    
    ss.iprint("%s -- %s --- TKE: %s " % (cnt,time,tke)  ) 
    cnt += 1
    if viz:

        fig = plt.figure(1)
        plt.clf()

        fig2 = plt.figure(2)
        plt.clf()

        dd = numpy.where( z == 0.0, 1.0, 0.0 )
        v = ss.PyMPI.zbar( dd*ss.variables[pvar].data )

        rho = ss.variables['rho'].data
        rhoL = ss.variables['rhoYh'].data
        rhoR = ss.variables['rhoYl'].data
        Yh  = ss.variables['Yh'].data
        u   = ss.variables['u'].data
        v   = ss.variables['v'].data
        p   = ss.variables['p'].data
        Et  = ss.variables['Et'].data            

        # Time specific BCs
        if (time > .010):
            if not leftOn:
                 wgt = numpy.exp( -(x-2.0)**2/.1**2 )
                 pleft = ss.PyMPI.sum3D( wgt * p ) / ss.PyMPI.sum3D( wgt )
                 eleft = ss.PyMPI.sum3D( wgt * Et ) / ss.PyMPI.sum3D( wgt )
                 rleft = ss.PyMPI.sum3D( wgt * rhoL ) / ss.PyMPI.sum3D( wgt )
                 rholeft = ss.PyMPI.sum3D( wgt * rho ) / ss.PyMPI.sum3D( wgt )
                 leftOn = True
                 
            ss.variables['Et'].data = numpy.where( x < 2.0 , eleft, Et )
            ss.variables['rhou'].data = numpy.where( x < 2.0 , 0.0  , u*rho )
            ss.variables['rho'].data = numpy.where( x < 2.0 , rholeft  , rho )
            ss.variables['rhoYh'].data = numpy.where( x < 2.0 , rleft  , rhoL )


        if (time > .016):
            if not rightOn:
                 wgt = numpy.exp( -(x-7.0)**2/.1**2 )
                 pright = ss.PyMPI.sum3D( wgt * p ) / ss.PyMPI.sum3D( wgt )
                 eright = ss.PyMPI.sum3D( wgt * Et ) / ss.PyMPI.sum3D( wgt )
                 rright = ss.PyMPI.sum3D( wgt * rhoR ) / ss.PyMPI.sum3D( wgt )
                 rhoright = ss.PyMPI.sum3D( wgt * rho ) / ss.PyMPI.sum3D( wgt )
                 rightOn = True
                 
            ss.variables['Et'].data = numpy.where( x > 7.0 , eright, Et )
            ss.variables['rhou'].data = numpy.where( x > 7.0 , 0.0  , u*rho )
            ss.variables['rho'].data = numpy.where( x > 7.0 , rhoright  , rho )
            ss.variables['rhoYl'].data = numpy.where( x > 7.0 , rright  , rhoR )

        
        if (ss.PyMPI.master and (cnt%viz_freq == 0)) and True:
            #dum = raw_input('Step?')
            

            # 2D contour plots
            ax = fig.add_subplot(2,2,1)
            im = ax.contourf( x[:,:,0], y[:,:,0], rho[:,:,0] ,32,cmap='jet')

            ax = fig.add_subplot(2,2,2)
            im = ax.contourf( x[:,:,0], y[:,:,0], Yh[:,:,0] ,32,cmap='jet')

            ax = fig.add_subplot(2,2,3)
            im = ax.contourf( x[:,:,0], y[:,:,0], p[:,:,0] ,32,cmap='jet')

            ax = fig.add_subplot(2,2,4)
            im = ax.contourf( x[:,:,0], y[:,:,0], u[:,:,0] ,32,cmap='jet')

            # 1D contour plots
            ax = fig2.add_subplot(2,2,1)
            im = ax.plot( x[:,0,0], rho[:,0,0] )

            ax = fig2.add_subplot(2,2,2)
            im = ax.plot( x[:,0,0], Yh[:,0,0] )

            ax = fig2.add_subplot(2,2,3)
            im = ax.plot( x[:,0,0],  p[:,0,0] )

            ax = fig2.add_subplot(2,2,4)
            im = ax.plot( x[:,0,0], u[:,0,0] )

            plt.pause(.001)

            
